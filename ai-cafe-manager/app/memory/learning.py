"""
learning.py
───────────
Scans historical feedback logs to identify "Golden Examples"—high-quality 
past interactions that should be used as few-shot examples for the agents.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

# Resolves to: ai-cafe-manager/data/feedback.json
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FEED_FILE = _PROJECT_ROOT / "data" / "feedback.json"

class LearningRetriever:
    """
    Retrieves high-score historical interactions to serve as 'Expert Examples' 
    for in-context learning.
    """

    def __init__(self, feedback_path: Path = _FEED_FILE):
        self.path = feedback_path

    def _load_feedback(self) -> List[Dict]:
        """Read the feedback ledger from disk."""
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to load feedback for learning: %s", e)
            return []

    def get_expert_examples(self, query: str, min_score: int = 8, top_k: int = 2) -> str:
        """
        Find past interactions that were rated highly and are relevant to the query.
        
        Returns a formatted markdown string of Few-Shot examples.
        """
        feedbacks = self._load_feedback()
        if not feedbacks:
            return ""

        # 1. Filter for quality (High scores only)
        high_quality = [f for f in feedbacks if f.get("score", 0) >= min_score]
        if not high_quality:
            return ""

        # 2. Rank by relevance (Keyword overlap)
        query_terms = set(query.lower().split())
        scored = []
        for example in high_quality:
            match_score = sum(1 for term in query_terms if term in example["query"].lower())
            if match_score > 0:
                scored.append((match_score, example))

        # 3. Format the top examples
        scored.sort(key=lambda x: x[0], reverse=True)
        top_examples = [ex for _, ex in scored[:top_k]]

        if not top_examples:
            return ""

        blocks = ["### 🌟 Expert Examples (How I successfully handled this before)"]
        for ex in top_examples:
            blocks.append(f"Past Query: {ex['query']}")
            blocks.append(f"Ideal Response: {ex['response']}\n")

        return "\n".join(blocks)
