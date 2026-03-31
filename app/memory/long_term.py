"""
long_term.py
────────────
Persistent JSON storage for long-term historical interactions.
Uses simple keyword matching for lightweight retrieval.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

# Resolves to: ai-cafe-manager/data/memory_store.json
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MEMORY_DIR = _PROJECT_ROOT / "data"
_MEMORY_FILE = _MEMORY_DIR / "memory_store.json"


class LongTermMemory:
    """
    Appends interactions to a persistent JSON log.
    Allows for basic keyword-based semantic retrieval to find related past interactions.
    """

    def __init__(self, filepath: Path = _MEMORY_FILE):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the JSON file and parent directories if they don't exist."""
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text("[]", encoding="utf-8")

    def load_memory(self) -> List[Dict[str, str]]:
        """Read the entire memory store from disk."""
        try:
            content = self.filepath.read_text(encoding="utf-8").strip()
            return json.loads(content) if content else []
        except Exception as e:
            logger.error("Failed to load long term memory: %s", e)
            return []

    def save_memory(self, tenant_id: int, query: str, response: str) -> None:
        """Append a new interaction to the persistent store tagged securely by tenant ID."""
        memories = self.load_memory()
        entry = {
            "tenant_id": tenant_id,
            "query": query,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        memories.append(entry)
        try:
            self.filepath.write_text(json.dumps(memories, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save long term memory: %s", e)

    def search_memory(self, tenant_id: int, query: str, top_k: int = 2) -> List[Dict[str, str]]:
        """
        Retrieve up to top_k past interactions securely matching the active tenant ID that share keywords.
        """
        memories = self.load_memory()
        if not memories:
            return []

        # STRICT ISOLATION: Filter by tenant_id first
        tenant_mems = [m for m in memories if m.get("tenant_id") == tenant_id]
        if not tenant_mems:
            return []

        # Simple lightweight token intersection scoring
        query_words = set(query.lower().split())
        scored_memories = []
        
        for mem in tenant_mems:
            # Check against both the stored query and response
            mem_text = f"{mem['query']} {mem['response']}".lower()
            score = sum(1 for word in query_words if word in mem_text)
            if score > 0:
                scored_memories.append((score, mem))
                
        # Sort by score descending and take top_k
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [mem for score, mem in scored_memories[:top_k]]
