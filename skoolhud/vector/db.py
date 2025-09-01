# skoolhud/vector/db.py
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

def get_client(persist_dir: Optional[str] = None):
    persist_dir = persist_dir or os.getenv("CHROMA_DIR", "vector_store")
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir, settings=Settings(allow_reset=False))
    return client

def get_or_create_collection(client, name: str):
    return client.get_or_create_collection(name=name, metadata={"hnsw:space":"cosine"})

def upsert_documents(col, ids: List[str], documents: List[str], metadatas: List[Dict[str, Any]], embeddings: Optional[List[List[float]]] = None):
    kwargs = {"ids": ids, "documents": documents, "metadatas": metadatas}
    if embeddings is not None:
        kwargs["embeddings"] = embeddings
    col.upsert(**kwargs)

def similarity_search(col, query: str, n_results: int = 5, where: Optional[Dict[str, Any]] = None):
    return col.query(query_texts=[query], n_results=n_results, where=where or {})
