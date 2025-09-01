# skoolhud/vector/ingest.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import uuid
import csv
import os

from sentence_transformers import SentenceTransformer
from skoolhud.vector.db import get_collection

REPORTS_DIR = Path("exports/reports")
TENANT = os.getenv("TENANT", "hoomans")
MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def _read_text_file(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return p.read_text(errors="ignore")

def _read_csv_top(p: Path, limit: int = 200) -> str:
    rows = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if headers:
            rows.append(" | ".join(headers))
        for i, r in enumerate(reader):
            rows.append(" | ".join(str(x) for x in r))
            if i + 1 >= limit:
                break
    return "\n".join(rows)

def _collect_documents() -> List[Dict]:
    docs: List[Dict] = []
    # Tenantisierte Pfade bevorzugen, sonst Fallback
    base_candidates = [REPORTS_DIR / TENANT, REPORTS_DIR]
    patterns = [
        "kpi_*.md",
        "leaderboard_movers.md",
        "leaderboard_delta_true.md",
        "member_health_summary.md",
        "member_health.csv",
        "members_snapshot_*.csv",
    ]
    for base in base_candidates:
        if not base.exists():
            continue
        for pat in patterns:
            for p in sorted(base.glob(pat)):
                if p.suffix.lower() == ".md":
                    text = _read_text_file(p)
                    doc = {
                        "id": f"{TENANT}:{p.name}:{uuid.uuid4().hex[:8]}",
                        "text": text,
                        "meta": {
                            "tenant": TENANT,
                            "type": "markdown",
                            "path": str(p),
                            "name": p.name,
                        },
                    }
                    docs.append(doc)
                elif p.suffix.lower() == ".csv":
                    text = _read_csv_top(p, limit=200)  # nicht zu groß
                    doc = {
                        "id": f"{TENANT}:{p.name}:{uuid.uuid4().hex[:8]}",
                        "text": text,
                        "meta": {
                            "tenant": TENANT,
                            "type": "csv",
                            "path": str(p),
                            "name": p.name,
                        },
                    }
                    docs.append(doc)
    return docs

def ingest():
    docs = _collect_documents()
    if not docs:
        print("Keine Dokumente gefunden unter exports/reports (tenantisiert oder global).")
        return
    print(f"Ingest {len(docs)} docs für tenant={TENANT}")

    model = SentenceTransformer(MODEL_NAME)
    collection = get_collection("skoolhud")

    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    metas = [d["meta"] for d in docs]

    # Embeddings berechnen
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()

    # Upsert
    collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metas)
    print(f"Upserted {len(ids)} docs in collection 'skoolhud'.")

if __name__ == "__main__":
    ingest()
