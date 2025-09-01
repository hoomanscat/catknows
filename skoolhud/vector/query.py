# skoolhud/vector/query.py
from __future__ import annotations
from typing import List
import os

from sentence_transformers import SentenceTransformer
from skoolhud.vector.db import get_collection

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def search(query: str, tenant: str = "hoomans", k: int = 5):
    model = SentenceTransformer(MODEL_NAME)
    q_emb = model.encode([query], normalize_embeddings=True).tolist()[0]

    col = get_collection("skoolhud")
    res = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        where={"tenant": tenant},  # Tenant-Filter (!)
        include=["embeddings", "metadatas", "documents", "distances"]
    )
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    print(f"\nTop {k} results for: '{query}' (tenant={tenant})")
    for i, (id_, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists), start=1):
        path = meta.get("path", "?")
        name = meta.get("name", "?")
        print(f"\n#{i}  score={1 - dist:.4f}  [{name}]")
        print(f"    {path}")
        snippet = (doc or "").strip()
        if len(snippet) > 400:
            snippet = snippet[:400] + " …"
        print("    ---")
        for line in snippet.splitlines()[:8]:
            print("    " + line)

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "wer sind die top movers der letzten 7 tage?"
    search(q)
