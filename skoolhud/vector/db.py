from __future__ import annotations

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.api import ClientAPI


def get_client(persist_dir: str = "vector_store") -> ClientAPI:
    """
    Erstellt/öffnet einen persistenten Chroma-Client im Ordner persist_dir.
    """
    p = Path(persist_dir).resolve()
    p.mkdir(parents=True, exist_ok=True)
    # Ab Chroma 0.5.x genügt der path-Parameter
    return chromadb.PersistentClient(path=str(p))


def get_or_create_collection(client: ClientAPI, name: str):
    """
    Holt oder erstellt eine Collection (cosine space).
    Hinweis: Wir nutzen erstmal KEINE Embedding-Funktion;
    Texte/Metadaten werden gespeichert, Embeddings hängen wir später an.
    """
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
