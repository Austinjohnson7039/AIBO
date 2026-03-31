"""
short_term.py
─────────────
In-memory storage for tracking the conversational session.
Stores the last N interactions to provide immediate context to LLM agents.
"""

from collections import deque
from typing import List, Dict


class ShortTermMemory:
    """
    Tracks the most recent N interactions in a thread-safe deque.
    This effectively acts as the 'Session' memory.
    """

    def __init__(self, limit: int = 5):
        """Initialise memory with a sliding window of size `limit` strictly per tenant."""
        self.limit = limit
        self.history_map: Dict[int, deque] = {}

    def add(self, tenant_id: int, query: str, response: str) -> None:
        """Append a new query/response pair to the tenant's sliding window."""
        if tenant_id not in self.history_map:
            self.history_map[tenant_id] = deque(maxlen=self.limit)
        self.history_map[tenant_id].append({"query": query, "response": response})

    def get_recent(self, tenant_id: int) -> List[Dict[str, str]]:
        """Return the recent conversation history chronologically for the tenant."""
        if tenant_id in self.history_map:
            return list(self.history_map[tenant_id])
        return []
