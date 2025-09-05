# skoolhud/vector/query.py
from __future__ import annotations
from typing import List
import os

from sentence_transformers import SentenceTransformer
from skoolhud.vector.db import get_client, get_or_create_collection
from skoolhud.config import get_tenant_slug

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _encode_text(model: SentenceTransformer, text: str):
    emb = model.encode([text], normalize_embeddings=True)
    # convert numpy/torch to plain list if needed
    if hasattr(emb, "tolist"):
        emb = emb.tolist()[0]
    else:
        emb = list(emb[0])
    return emb


def search(query: str, tenant: str | None = None, k: int = 5, collection_name: str = "skoolhud"):
    tenant = get_tenant_slug(tenant)
    """Generic search against a named collection (keeps backward compatibility)."""
    model = SentenceTransformer(MODEL_NAME)
    q_emb = _encode_text(model, query)

    client = get_client()
    col = get_or_create_collection(client, collection_name)
    res = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        where={"tenant": tenant},
        include=["embeddings", "metadatas", "documents", "distances"],
    )
    # Chroma may return None or nested empty lists; guard extraction for typing tools
    def _first_list_field(result_dict, key: str):
        val = result_dict.get(key)
        if not val or not isinstance(val, list):
            return []
        first = val[0]
        if not first or not isinstance(first, list):
            return []
        return first

    ids = _first_list_field(res, "ids")
    docs = _first_list_field(res, "documents")
    metas = _first_list_field(res, "metadatas")
    dists = _first_list_field(res, "distances")

    print(f"\nTop {k} results for: '{query}' (tenant={tenant}) collection={collection_name}")
    for i, (id_, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists), start=1):
        path = meta.get("path", "?")
        title = meta.get("filename", meta.get("name", "?"))
        score = 1 - dist if dist is not None else None
        print(f"\n#{i}  score={score:.4f}  [{title}]")
        print(f"    {path}")
        snippet = (doc or "").strip()
        if len(snippet) > 400:
            snippet = snippet[:400] + " "
        print("    ---")
        for line in snippet.splitlines()[:8]:
            print("    " + line)


def search_reports(query: str, tenant: str | None = None, k: int = 5, collection_name: str = "skool_reports"):
    tenant = get_tenant_slug(tenant)
    """Convenience helper that searches the reports collection for a tenant."""
    return search(query=query, tenant=tenant, k=k, collection_name=collection_name)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "who joined last week"
    # default: search reports collection to show agent/report hits
    search_reports(q)
