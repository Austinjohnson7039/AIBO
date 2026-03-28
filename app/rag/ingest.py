"""
ingest.py
─────────
FAQ ingestion pipeline: load → chunk → embed → index → persist.

Responsibilities:
  1. Load the FAQ text file.
  2. Split content into overlapping chunks (word-based, not character-based).
  3. Generate embeddings for every chunk via the OpenAI API (one batch call).
  4. Build a FAISS flat index and add the embeddings.
  5. Persist the index + chunk metadata to disk for the Retriever to consume.

Design decisions:
  - Word-level chunking is more semantically stable than character-based chunking
    because it never splits mid-word.
  - Overlap ensures context is preserved across chunk boundaries.
  - Metadata (chunk text + id) is stored in a sidecar JSON file so the Retriever
    can return human-readable results without decoding the binary index.
  - All paths are derived from __file__ so the script is location-independent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import faiss

from app.rag.embeddings import get_embeddings, EMBEDDING_DIM

logger = logging.getLogger(__name__)

# ─── Path constants (relative to project root) ────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[2]          # ai-cafe-manager/
_FAQ_PATH     = _PROJECT_ROOT / "data" / "faq.txt"
_INDEX_DIR    = _PROJECT_ROOT / "faiss_index"
_INDEX_PATH   = _INDEX_DIR / "index.bin"
_META_PATH    = _INDEX_DIR / "metadata.json"

# ─── Chunking ─────────────────────────────────────────────────────────────────

def _load_faq(path: Path = _FAQ_PATH) -> str:
    """Read the raw FAQ text file and return its contents."""
    if not path.exists():
        raise FileNotFoundError(f"FAQ file not found at: {path}")
    return path.read_text(encoding="utf-8").strip()


def _chunk_text(
    text: str,
    chunk_size: int = 50,
    overlap: int = 10,
) -> list[str]:
    """
    Split text into overlapping word-level chunks.

    Args:
        text:       Raw document text.
        chunk_size: Maximum number of words per chunk.
        overlap:    Number of words shared between consecutive chunks.

    Returns:
        List of text chunks (strings).

    Notes:
        - Each FAQ line is treated as a standalone entry; we preserve line
          boundaries so a Q&A pair is never merged with another.
        - Short lines that are already below chunk_size are kept as-is.
    """
    chunks: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        words = line.split()

        if len(words) <= chunk_size:
            # Line fits in a single chunk — keep it whole
            chunks.append(line)
        else:
            # Slide a window across the words
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk = " ".join(words[start:end])
                chunks.append(chunk)
                if end == len(words):
                    break
                start += chunk_size - overlap  # step forward with overlap

    return chunks


def _build_metadata(chunks: list[str]) -> list[dict]:
    """Wrap each chunk in a metadata envelope."""
    return [{"chunk_id": i, "text": chunk} for i, chunk in enumerate(chunks)]


# ─── FAISS index builder ───────────────────────────────────────────────────────

def _create_faiss_index(embeddings: list[list[float]]) -> faiss.IndexFlatIP:
    """
    Build a FAISS flat inner-product index from a list of embedding vectors.

    IndexFlatIP with normalised vectors is equivalent to cosine similarity —
    ideal for semantic search.

    Args:
        embeddings: List of float vectors (all must have length == EMBEDDING_DIM).

    Returns:
        A populated faiss.IndexFlatIP instance.
    """
    matrix = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(matrix)                        # normalise for cosine sim

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(matrix)                                 # type: ignore[arg-type]
    logger.debug("FAISS index built with %d vectors.", index.ntotal)
    return index


# ─── Persistence ──────────────────────────────────────────────────────────────

def _save_index(index: faiss.IndexFlatIP, metadata: list[dict]) -> None:
    """Write the FAISS binary index and JSON metadata sidecar to disk."""
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(_INDEX_PATH))
    logger.info("FAISS index saved → %s", _INDEX_PATH)

    _META_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Metadata saved  → %s (%d chunks)", _META_PATH, len(metadata))


# ─── Public entry point ───────────────────────────────────────────────────────

def ingest_documents(
    faq_path: Optional[Path] = None,
    chunk_size: int = 50,
    overlap: int = 10,
    force: bool = False,
) -> None:
    """
    Full ingestion pipeline: load → chunk → embed → index → persist.

    Args:
        faq_path:   Override the default FAQ file path (useful for testing).
        chunk_size: Words per chunk (default 50 — balances detail and context).
        overlap:    Words of overlap between consecutive chunks (default 10).
        force:      If True, re-ingest even when an index already exists.

    Raises:
        FileNotFoundError: If the FAQ file is missing.
        EnvironmentError:  If the OpenAI API key is not configured.
    """
    source = faq_path or _FAQ_PATH

    if _INDEX_PATH.exists() and not force:
        logger.info(
            "FAISS index already exists at %s. "
            "Pass force=True to re-ingest.",
            _INDEX_PATH,
        )
        return

    logger.info("Starting ingestion from: %s", source)

    # 1. Load
    raw_text = _load_faq(source)
    logger.info("Loaded FAQ (%d chars).", len(raw_text))

    # 2. Chunk
    chunks = _chunk_text(raw_text, chunk_size=chunk_size, overlap=overlap)
    logger.info("Split into %d chunks.", len(chunks))

    if not chunks:
        raise ValueError("No chunks produced from the FAQ file — check its contents.")

    # 3. Embed (one batch API call)
    logger.info("Generating embeddings via OpenAI (batch size=%d)…", len(chunks))
    embeddings = get_embeddings(chunks)
    logger.info("Embeddings received (%d × %d).", len(embeddings), len(embeddings[0]))

    # 4. Index
    index = _create_faiss_index(embeddings)

    # 5. Build metadata + persist
    metadata = _build_metadata(chunks)
    _save_index(index, metadata)

    logger.info("✅ Ingestion complete. %d chunks indexed.", len(chunks))


# ─── CLI helper ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    force_flag = "--force" in sys.argv
    ingest_documents(force=force_flag)
