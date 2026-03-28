"""
embeddings.py
─────────────
Local, offline embedding generation using fastembed.
Replaces the OpenAI API requirement for constructing the RAG index.
Allows the backend to remain 100% free from OpenAI dependencies.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384

# Global singleton for the local model to avoid reloading weights every call.
_EMBEDDING_CLIENT = None


def _get_client() -> TextEmbedding:
    """Lazy-load the embedding model into memory exactly once."""
    global _EMBEDDING_CLIENT
    if _EMBEDDING_CLIENT is None:
        logger.info(f"Loading local embedding model: {EMBEDDING_MODEL}")
        _EMBEDDING_CLIENT = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _EMBEDDING_CLIENT


def _clean(text: str) -> str:
    """Normalise whitespace."""
    return text.replace("\n", " ").strip()


# ─── Public API ───────────────────────────────────────────────────────────────

def get_embedding(text: str, api_key: Optional[str] = None) -> list[float]:
    """
    Generate a single embedding vector for the given text.
    The api_key argument is ignored since this is fully local.
    """
    client = _get_client()
    cleaned = _clean(text)
    
    # fastembed returns a generator yielding numpy arrays
    embedding_gen = client.embed([cleaned])
    return list(embedding_gen)[0].tolist()


def get_embeddings(texts: list[str], api_key: Optional[str] = None) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using fastembed.
    """
    if not texts:
        raise ValueError("texts must be a non-empty list.")

    client = _get_client()
    cleaned = [_clean(t) for t in texts]

    # embed() returns a generator of numpy arrays. Convert to lists.
    embedding_gen = client.embed(cleaned)
    return [vec.tolist() for vec in embedding_gen]
