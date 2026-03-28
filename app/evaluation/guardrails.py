"""
guardrails.py
─────────────
Rule-based heuristic checks for AI responses.
Catches basic safety violations and hallucinatory language before LLM grading.
"""

class Guardrails:
    """Fast, string-matching safety checks on generated responses."""

    def __init__(self, max_length: int = 1500):
        self.max_length = max_length
        self.uncertain_phrases = [
            "i guess",
            "maybe",
            "i'm not sure",
            "perhaps",
            "it might be",
            "possibly"
        ]

    def check(self, response: str) -> dict:
        """
        Scan for overt uncertainty or excessively long rambles.
        
        Args:
            response: The generated string from an agent.
            
        Returns:
            dict: {"safe": bool, "issues": list[str]}
        """
        issues = []
        lower_resp = response.lower()

        # 1. Length constraint (prevent API abuse / looping)
        if len(response) > self.max_length:
            issues.append("Response too long; exceeded max length.")

        # 2. Heuristic hallucination / guessing check
        for phrase in self.uncertain_phrases:
            if phrase in lower_resp:
                issues.append(f"Uncertain language flagged: '{phrase}'")

        # 3. Final safety determination
        # We only consider it truly "unsafe" if it's excessively long (potential loop)
        # Uncertain language is now just an "issue" for the score, not a block.
        is_safe = not any("Response too long" in issue for issue in issues)

        return {
            "safe": is_safe,
            "issues": issues
        }
