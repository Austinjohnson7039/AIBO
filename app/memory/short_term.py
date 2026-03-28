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
        """Initialise memory with a sliding window of size `limit`."""
        self.limit = limit
        self.history: deque[Dict[str, str]] = deque(maxlen=limit)

    def add(self, query: str, response: str) -> None:
        """Append a new query/response pair to the sliding window."""
        self.history.append({"query": query, "response": response})

    def get_recent(self) -> List[Dict[str, str]]:
        """Return the recent conversation history chronologically."""
        return list(self.history)
