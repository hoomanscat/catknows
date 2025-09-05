# skoolhud/vector/ingest.py
from __future__ import annotations
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.vector.db import get_client, get_or_create_collection, upsert_documents
from skoolhud.vector.embed import get_embedder

def _member_to_doc(m: Member) -> Dict[str, str]:
    # Textfeld für Semantik
    # Fix: SQLAlchemy columns need explicit str conversion
    def safe_str(val):
        try:
            return str(val) if val is not None else ''
        except Exception:
            return ''
    links = [safe_str(getattr(m, attr, None)) for attr in ["link_website", "link_linkedin", "link_instagram", "link_youtube", "link_facebook"] if getattr(m, attr, None)]
    parts = [
        f"Name: {safe_str(m.name)}",
        f"Handle: {safe_str(m.handle)}",
        f"Location: {safe_str(m.location)}",
        f"Bio: {safe_str(m.bio)}",
        f"Links: {', '.join(links)}"
    ]
    return {
        "text": "\n".join(parts).strip()
    }

def ingest_members_to_vector(tenant: str, collection_name: str = "skool_members", batch_size: int = 512):

    print(f"[vector] Starte Ingest für tenant={tenant}")
    s: Session = SessionLocal()
    try:
        rows: List[Member] = s.query(Member).filter(Member.tenant == tenant).all()
        print(f"[vector] Gefundene Member: {len(rows)}")
        if rows:
            print(f"[vector] Beispiel-Member: {rows[0].__dict__}")
    finally:
        s.close()

    if not rows:
        print(f"[vector] Keine Members für tenant={tenant}")
        return

    client = get_client()
    col = get_or_create_collection(client, collection_name)
    embed = get_embedder()

    ids, docs, metas = [], [], []
    for m in rows:
        # Fix: SQLAlchemy columns need explicit str conversion
        user_id_val = str(getattr(m, "user_id", ""))
        if not user_id_val:
            continue
        doc = _member_to_doc(m)
        ids.append(f"{tenant}:{user_id_val}")
        metas.append({
            "tenant": tenant,
            "user_id": user_id_val,
            "name": str(getattr(m, "name", "")),
            "level": getattr(m, "level_current", 0) or 0,
            "points_all": getattr(m, "points_all", 0) or 0,
        })
        docs.append(doc["text"])

        # Batch schreiben
        if len(ids) >= batch_size:
            print(f"[vector] Batchgröße erreicht: {len(ids)}. Starte Embedding und Upsert...")
            embs = embed(docs)
            print(f"[vector] Embeddings erzeugt: {len(embs)}")
            # Fix: convert PyTorch tensors to lists for ChromaDB
            def tensor_to_list(e):
                if hasattr(e, 'tolist'):
                    return e.tolist()
                return e
            embs = [tensor_to_list(e) for e in embs]
            upsert_documents(col, ids, docs, metas, embeddings=embs)
            print(f"[vector] upsert batch: {len(ids)}")
            ids, docs, metas = [], [], []

    if ids:
        print(f"[vector] Letzter Batch: {len(ids)}. Starte Embedding und Upsert...")
        embs = embed(docs)
        print(f"[vector] Embeddings erzeugt: {len(embs)}")
        # Fix: convert PyTorch tensors to lists for ChromaDB
        def tensor_to_list(e):
            if hasattr(e, 'tolist'):
                return e.tolist()
            return e
        embs = [tensor_to_list(e) for e in embs]
        upsert_documents(col, ids, docs, metas, embeddings=embs)
        print(f"[vector] upsert batch: {len(ids)}")

    print(f"[vector] DONE tenant={tenant}, total={len(rows)} → collection={collection_name}")

# The module exposes `ingest_members_to_vector` for programmatic use.
# Do not run the ingest on import — callers (CLI, scripts) should invoke it explicitly.
def ingest_reports_to_vector(
    tenant: str,
    patterns: Optional[List[str]] = None,
    collection_name: str = "skool_reports",
    batch_size: int = 128,
):
    """Ingest textual report files (markdown, txt, csv) from exports/reports/<tenant>/ into the vector store.

    - patterns: glob patterns (relative to exports/reports/<tenant>) to include, e.g. ['ai_kpi_summary_*.md']
    - collection_name: chroma collection name to upsert into
    """
    from pathlib import Path
    import re

    print(f"[vector] Starte Report-Ingest für tenant={tenant} patterns={patterns} collection={collection_name}")
    base = Path("exports") / "reports" / tenant
    if not base.exists():
        print(f"[vector] Kein reports-Verzeichnis für tenant={tenant}: {base}")
        return

    # sensible defaults if not provided
    if not patterns:
        patterns = [
            "ai_kpi_summary_*.md",
            "ai_health_plan_*.md",
            "new_joiners_*.md",
            "leaderboard_movers*.md",
            "alerts*.md",
            "celebrations*.md",
            "shoutouts*.md",
            "snapshot_*.md",
        ]

    # collect files
    files = []
    for pat in patterns:
        files.extend(sorted(base.glob(pat)))

    if not files:
        print(f"[vector] Keine Report-Dateien gefunden für tenant={tenant} (patterns={patterns})")
        return

    client = get_client()
    col = get_or_create_collection(client, collection_name)
    embed = get_embedder()

    ids, docs, metas = [], [], []

    def strip_markdown(txt: str) -> str:
        # very light markdown stripping: remove code fences, images, and headings
        txt = re.sub(r"```[\s\S]*?```", " ", txt)
        txt = re.sub(r"!\[[^\]]*\]\([^\)]+\)", " ", txt)
        txt = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", txt)
        txt = re.sub(r"^#+\s*", "", txt, flags=re.MULTILINE)
        return txt.strip()

    for p in files:
        try:
            text = p.read_text(encoding='utf-8')
        except Exception:
            continue
        text = strip_markdown(text)
        if not text:
            continue

        fid = f"{tenant}:report:{p.name}:{int(p.stat().st_mtime)}"
        ids.append(fid)
        docs.append(text)
        metas.append({
            "tenant": tenant,
            "filename": p.name,
            "path": str(p),
            "mtime": int(p.stat().st_mtime),
        })

        if len(ids) >= batch_size:
            print(f"[vector] Report-Batchgröße erreicht: {len(ids)}. Starte Embedding und Upsert...")
            embs = embed(docs)
            def tensor_to_list(e):
                if hasattr(e, 'tolist'):
                    return e.tolist()
                return e
            embs = [tensor_to_list(e) for e in embs]
            upsert_documents(col, ids, docs, metas, embeddings=embs)
            print(f"[vector] upsert report batch: {len(ids)}")
            ids, docs, metas = [], [], []

    if ids:
        print(f"[vector] Letzter Report-Batch: {len(ids)}. Starte Embedding und Upsert...")
        embs = embed(docs)
        def tensor_to_list(e):
            if hasattr(e, 'tolist'):
                return e.tolist()
            return e
        embs = [tensor_to_list(e) for e in embs]
        upsert_documents(col, ids, docs, metas, embeddings=embs)
        print(f"[vector] upsert report batch: {len(ids)}")

    print(f"[vector] DONE report-ingest tenant={tenant} total_files={len(files)} → collection={collection_name}")
