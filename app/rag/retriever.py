"""
retriever.py
────────────
FAISS-backed semantic retriever for the AI Cafe Manager RAG pipeline.

Responsibilities:
  1. Load the persisted FAISS index and metadata sidecar from disk.
  2. Convert an incoming query to an embedding.
  3. Search the index for the nearest neighbours.
  4. Return ranked results with text and cosine similarity score.

Design decisions:
  - The Retriever is a class rather than module-level functions so that the
    index is loaded once and reused across multiple search calls.
  - load_index() is separate from __init__ so callers control when I/O happens
    (useful for lazy loading inside FastAPI lifespan).
  - Scores are the raw inner-product values from FAISS (≈ cosine similarity
    after normalisation). They are rounded for readability but not clipped,
    so callers can apply their own thresholds.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import faiss

from app.rag.embeddings import get_embedding, EMBEDDING_DIM

logger = logging.getLogger(__name__)

# ─── Path constants ────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INDEX_DIR    = _PROJECT_ROOT / "faiss_index"
_INDEX_PATH   = _INDEX_DIR / "index.bin"
_META_PATH    = _INDEX_DIR / "metadata.json"


# ─── Result type ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RetrievalResult:
    """A single ranked retrieval result."""
    chunk_id: int
    text: str
    score: float

    def to_dict(self) -> dict:
        return {"chunk_id": self.chunk_id, "text": self.text, "score": self.score}


# ─── Retriever ────────────────────────────────────────────────────────────────

@dataclass
class Retriever:
    """
    Semantic search over the FAISS index built by ingest.py.

    Usage:
        retriever = Retriever()
        retriever.load_index()
        results = retriever.search("Do you deliver?")
        for r in results:
            print(r.score, r.text)
    """

    index_path: Path = field(default_factory=lambda: _INDEX_PATH)
    meta_path: Path  = field(default_factory=lambda: _META_PATH)

    # Internal state — populated by load_index()
    _index: Optional[faiss.IndexFlatIP] = field(default=None, init=False, repr=False)
    _metadata: list[dict]               = field(default_factory=list, init=False, repr=False)

    # ── Loading ──────────────────────────────────────────────────────────────

    def load_index(self) -> None:
        """
        Load the FAISS index and metadata from disk.

        Should be called once before any search() calls.
        Safe to call multiple times — subsequent calls are no-ops.

        Raises:
            FileNotFoundError: If the index or metadata file does not exist.
                               Run `python -m app.rag.ingest` to create them.
        """
        if self._index is not None:
            logger.debug("Index already loaded — skipping.")
            return

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {self.index_path}. "
                "Run the ingestion pipeline first:\n"
                "  python -m app.rag.ingest"
            )
        if not self.meta_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found at {self.meta_path}. "
                "Re-run the ingestion pipeline to regenerate it."
            )

        self._index = faiss.read_index(str(self.index_path))
        self._metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))

        logger.info(
            "Retriever ready — index: %d vectors, metadata: %d chunks.",
            self._index.ntotal,
            len(self._metadata),
        )

    # ── Searching ─────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> list[RetrievalResult]:
        """
        Retrieve the top-k most semantically relevant chunks for a query.

        Args:
            query: Natural-language question or statement.
            top_k: Number of results to return (default 3).

        Returns:
            List of RetrievalResult objects, sorted by descending score.

        Raises:
            RuntimeError:  If load_index() has not been called yet.
            ValueError:    If top_k < 1.
        """
        if self._index is None:
            raise RuntimeError(
                "Index is not loaded. Call load_index() before search()."
            )
        if top_k < 1:
            raise ValueError(f"top_k must be ≥ 1, got {top_k}.")

        # Clamp top_k to available vectors
        available = self._index.ntotal
        k = min(top_k, available)

        logger.debug("Searching for top-%d chunks for query: %r", k, query[:80])

        # 1. Embed the query
        query_vec = np.array([get_embedding(query)], dtype=np.float32)
        faiss.normalize_L2(query_vec)                  # match ingest normalisation

        # 2. Search
        scores, indices = self._index.search(query_vec, k)

        # 3. Build results
        results: list[RetrievalResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                # FAISS returns -1 for missing results (shouldn't happen with FlatIP)
                continue
            meta = self._metadata[idx]
            results.append(
                RetrievalResult(
                    chunk_id=meta["chunk_id"],
                    text=meta["text"],
                    score=round(float(score), 4),
                )
            )

        logger.debug("Retrieved %d results.", len(results))
        return results

    def search_as_dicts(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Convenience wrapper — returns plain dicts instead of dataclasses.
        Useful when the results need to be JSON-serialised directly.
        """
        return [r.to_dict() for r in self.search(query, top_k=top_k)]

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        """True if the index is ready for searching."""
        return self._index is not None

    @property
    def num_chunks(self) -> int:
        """Number of chunks indexed (0 if not loaded)."""
        return self._index.ntotal if self._index else 0


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Do you deliver?"

    retriever = Retriever()
    retriever.load_index()

    print(f"\n🔍 Query: {query!r}")
    print(f"   Index size: {retriever.num_chunks} chunks\n")

    results = retriever.search(query, top_k=3)

    for rank, result in enumerate(results, start=1):
        print(f"  [{rank}] score={result.score:.4f}")
        print(f"       {result.text}")
        print()
