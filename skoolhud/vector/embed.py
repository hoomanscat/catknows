# skoolhud/vector/embed.py
from __future__ import annotations
import os
from typing import Callable, List

_EMBEDDER = None

def _local_embedder() -> Callable[[List[str]], List[List[float]]]:
    # Lokales Mini-Modell, keine API nötig.
    from sentence_transformers import SentenceTransformer
    model_name = os.getenv("SENTENCE_TRANSFORMERS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    def encode(texts: List[str]) -> List[List[float]]:
        return model.encode(texts, convert_to_numpy=False, normalize_embeddings=True).tolist()
    return encode

def _openai_embedder() -> Callable[[List[str]], List[List[float]]]:
    # Optionaler Pfad über OpenAI (nur wenn explizit gewünscht).
    # Benötigt: OPENAI_API_KEY, OPENAI_EMBED_MODEL (z.B. "text-embedding-3-small")
    import openai
    openai.api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    def encode(texts: List[str]) -> List[List[float]]:
        # Batch-Call
        resp = openai.Embeddings.create(model=model, input=texts)
        return [d["embedding"] for d in resp["data"]]
    return encode

def get_embedder() -> Callable[[List[str]], List[List[float]]]:
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    use_openai = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() in ("1","true","yes","y")
    _EMBEDDER = _openai_embedder() if use_openai else _local_embedder()
    return _EMBEDDER
