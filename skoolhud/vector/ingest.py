# skoolhud/vector/ingest.py
from __future__ import annotations
from typing import List, Dict
from sqlalchemy.orm import Session
from skoolhud.db import SessionLocal
from skoolhud.models import Member
from skoolhud.vector.db import get_client, get_or_create_collection, upsert_documents
from skoolhud.vector.embed import get_embedder

def _member_to_doc(m: Member) -> Dict[str, str]:
    # Textfeld für Semantik
    parts = [
        f"Name: {m.name or ''}",
        f"Handle: {m.handle or ''}",
        f"Location: {m.location or ''}",
        f"Bio: {m.bio or ''}",
        f"Links: {', '.join([_ for _ in [m.link_website, m.link_linkedin, m.link_instagram, m.link_youtube, m.link_facebook] if _])}"
    ]
    return {
        "text": "\n".join(parts).strip()
    }

def ingest_members_to_vector(tenant: str, collection_name: str = "skool_members", batch_size: int = 512):
    s: Session = SessionLocal()
    try:
        rows: List[Member] = s.query(Member).filter(Member.tenant == tenant).all()
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
        if not m.user_id:
            continue
        doc = _member_to_doc(m)
        ids.append(f"{tenant}:{m.user_id}")
        docs.append(doc["text"])
        metas.append({
            "tenant": tenant,
            "user_id": m.user_id,
            "name": m.name or "",
            "level": m.level_current or 0,
            "points_all": m.points_all or 0,
        })

        # Batch schreiben
        if len(ids) >= batch_size:
            embs = embed(docs)
            upsert_documents(col, ids, docs, metas, embeddings=embs)
            print(f"[vector] upsert batch: {len(ids)}")
            ids, docs, metas = [], [], []

    if ids:
        embs = embed(docs)
        upsert_documents(col, ids, docs, metas, embeddings=embs)
        print(f"[vector] upsert batch: {len(ids)}")

    print(f"[vector] DONE tenant={tenant}, total={len(rows)} → collection={collection_name}")
