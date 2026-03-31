"""
feedback.py
───────────
Persistent JSON log for storing interactions alongside their 
evaluation scores and guardrail flags.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Relative to ai-cafe-manager/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FEEDBACK_DIR = _PROJECT_ROOT / "data"
_FEEDBACK_FILE = _FEEDBACK_DIR / "feedback.json"


class FeedbackStore:
    """Appends evaluated system interactions to a historical JSON log."""

    def __init__(self, filepath: Path = _FEEDBACK_FILE):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the JSON file and parent directories if they don't exist."""
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text("[]", encoding="utf-8")

    def load_feedback(self) -> list:
        """Fetch all stored feedback."""
        try:
            content = self.filepath.read_text(encoding="utf-8").strip()
            return json.loads(content) if content else []
        except Exception as e:
            logger.error("Failed to load feedback: %s", e)
            return []

    def save_feedback(
        self, tenant_id: int, query: str, response: str, score: int, issues: list[str]
    ) -> None:
        """Append a newly evaluated interaction object to the persistent store natively isolated by schema ID."""
        from datetime import datetime
        feedbacks = self.load_feedback()
        feedbacks.append({
            "tenant_id": tenant_id,
            "query": query,
            "response": response,
            "score": score,
            "issues": issues,
            # BUG FIX (BUG 15): Was missing timestamp. Required for recency-weighted learning.
            "timestamp": datetime.utcnow().isoformat()
        })
        try:
            self.filepath.write_text(json.dumps(feedbacks, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to format/save feedback: %s", e)
