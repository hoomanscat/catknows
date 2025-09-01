# skoolhud/vector/db.py
from pathlib import Path
import chromadb

PERSIST_DIR = Path("data_lake/vectors").resolve()

def get_client():
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    return client

def get_collection(name: str = "skoolhud"):
    client = get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )
