"""
learning.py
───────────
Scans historical feedback logs to identify "Golden Examples"—high-quality 
past interactions that should be used as few-shot examples for the agents.

BUG FIX (BUG 15): Added recency-weighted scoring so recent high-quality
interactions rank higher than old stale ones. Without this, 6-month-old
feedback ranked identically to yesterday's — defeating self-learning.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

# Resolves to: AIBO root / data / feedback.json
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FEED_FILE = _PROJECT_ROOT / "data" / "feedback.json"

class LearningRetriever:
    """
    Retrieves high-score historical interactions to serve as 'Expert Examples' 
    for in-context learning.
    
    Scoring formula: final_score = keyword_overlap * recency_weight * quality_score
    - keyword_overlap: how many query terms match the stored example
    - recency_weight: exponential decay — examples from 30 days ago get 0.5x weight
    - quality_score: normalized 0-1 from the raw eval score (1-10)
    """

    def __init__(self, feedback_path: Path = _FEED_FILE, decay_half_life_days: float = 30.0):
        self.path = feedback_path
        # Half-life in days: interactions from `decay_half_life_days` ago get 0.5x weight
        self.decay_half_life_days = decay_half_life_days

    def _load_feedback(self) -> List[Dict]:
        """Read the feedback ledger from disk."""
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to load feedback for learning: %s", e)
            return []

    def _recency_weight(self, timestamp_str: str) -> float:
        """
        Exponential decay weight based on age of the feedback entry.
        Returns 1.0 for brand-new entries, 0.5 for entries that are `decay_half_life_days` old.
        Entries with no timestamp get a neutral weight of 0.5.
        """
        if not timestamp_str:
            return 0.5
        try:
            ts = datetime.fromisoformat(timestamp_str)
            # Make timezone-aware if naive
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            age_days = (now - ts).total_seconds() / 86400.0
            # Exponential decay: weight = 2^(-age / half_life)
            return math.pow(2.0, -age_days / self.decay_half_life_days)
        except Exception:
            return 0.5

    def get_expert_examples(self, tenant_id: int, query: str, min_score: int = 8, top_k: int = 2) -> str:
        """
        Find past interactions securely mapped to the Tenant ID that were rated highly.
        Uses recency-weighted keyword scoring for ranking.
        
        Returns a formatted markdown string of Few-Shot examples.
        """
        feedbacks = self._load_feedback()
        if not feedbacks:
            return ""

        # 1. Strict Isolation + Filter for quality (High scores only)
        high_quality = [
            f for f in feedbacks 
            if f.get("tenant_id") == tenant_id and f.get("score", 0) >= min_score
        ]
        if not high_quality:
            return ""

        # 2. Rank by recency-weighted keyword relevance
        query_terms = set(query.lower().split())
        scored = []
        for example in high_quality:
            keyword_match = sum(1 for term in query_terms if term in example.get("query", "").lower())
            if keyword_match > 0:
                # Normalize score to 0-1 range (scores are 1-10)
                quality_weight = example.get("score", 5) / 10.0
                # Apply recency decay
                recency = self._recency_weight(example.get("timestamp", ""))
                # Combined weighted score
                final_score = keyword_match * recency * quality_weight
                scored.append((final_score, example))

        if not scored:
            return ""

        # 3. Format the top examples
        scored.sort(key=lambda x: x[0], reverse=True)
        top_examples = [ex for _, ex in scored[:top_k]]

        blocks = ["### 🌟 Expert Examples (How I successfully handled this before)"]
        for ex in top_examples:
            blocks.append(f"Past Query: {ex['query']}")
            blocks.append(f"Ideal Response: {ex['response']}\n")

        return "\n".join(blocks)
