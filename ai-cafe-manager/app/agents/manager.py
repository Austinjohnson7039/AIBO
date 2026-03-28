"""
manager.py
──────────
Manager Agent — top-level decision-routing agent.
Classifies user queries into discrete agent capabilities.
"""

from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI, OpenAIError

from app.config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# ─── Manager ──────────────────────────────────────────────────────────────────

class ManagerAgent:
    """
    Decides which specialised agent (analyst or support) should handle
    an incoming query based on intent classification.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialise the ManagerAgent with an OpenAI client."""
        key = api_key or GROQ_API_KEY
        if key:
            self.client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)
        else:
            self.client = None

    def decide_agent(self, query: str, context: str = "") -> str:
        """
        Route the query to either 'analyst', 'support', or 'operations'.
        
        Args:
            query: The natural language user query.
            context: Optional conversation history to resolve follow-up intents.
            
        Returns:
            A string literal indicating the routing destination.
            Defaults to 'support' if classification fails or the API errors.
        """
        logger.info("Manager Agent routing query: %r", query[:50])
        
        if not self.client:
            logger.error("ManagerAgent lacks a GROQ_API_KEY. Defaulting to 'support'.")
            return "support"

        system_prompt = (
            "You are a decision-making AI that routes queries.\n\n"
            "If the query (or the context of the conversation) is about:\n"
            "* adding items to inventory\n"
            "* increasing stock\n"
            "* recording a sale\n"
            "* updating quantity\n"
            "* new inventory items\n"
            "  - This includes follow-up answers (e.g., providing a quantity or detail asked by the AI)\n"
            "  → return 'operations'\n\n"
            "If the query is about analysis of data:\n"
            "* trends, revenue, totals\n"
            "  → return 'analyst'\n\n"
            "Else, return 'support'.\n\n"
            "Return ONLY one word: either 'analyst', 'support', or 'operations'."
        )

        user_prompt = f"Query: {query}\n\nExisting Context:\n{context}"

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0  # Must be strictly deterministic
            )
            decision = response.choices[0].message.content.strip().lower()
            
            # Clean up potential LLM hallucination
            decision = decision.replace("'", "").replace('"', '')
            
            if "analyst" in decision:
                return "analyst"
            elif "support" in decision:
                return "support"
            elif "operations" in decision:
                return "operations"
            else:
                logger.warning(
                    "Unexpected decision %r from LLM. Defaulting to 'support'.", 
                    decision
                )
                return "support"

        except OpenAIError as e:
            logger.error("OpenAI API routing error: %s. Defaulting to 'support'.", e)
            return "support"
        except Exception as e:
            logger.exception("Unexpected routing error: %s. Defaulting to 'support'.", e)
            return "support"
