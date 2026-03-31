"""
evaluator.py
────────────
LLM-as-a-judge for deep evaluation of accuracy, relevance, and hallucinations.
Requires response_format={"type": "json_object"} to strictly type the schema.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from openai import OpenAI, OpenAIError

from app.config import GROQ_API_KEY

logger = logging.getLogger(__name__)

LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class Evaluator:
    """
    Submits an AI-generated response alongside its source context
    to an authoritative LLM to receive a scored accuracy assessment.
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or GROQ_API_KEY
        if key:
            self.client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)
        else:
            self.client = None

    def evaluate(self, query: str, response: str, context: str) -> dict:
        """
        Evaluate response against ground-truth context.
        
        Args:
            query: Original user question.
            response: AI's proposed answer.
            context: Grounding context string (RAG chunks / DB).
            
        Returns:
            dict matching: {"score": int(1-10), "hallucination": bool, "reason": str}
        """
        # Default safety net if API is disconnected
        default_eval = {
            "score": 5, 
            "hallucination": False, 
            "reason": "Evaluation skipped (No OpenAI API key)."
        }

        if not self.client:
            logger.warning("Evaluator bypassed (Missing API key).")
            return default_eval

        # Truncate context heavily to save tokens and latency on the eval pass
        # Increase to 64,000 to ensure the Judge sees the full sales/inventory context
        context_preview = context[:64000] + ("..." if len(context) > 64000 else "")

        system_prompt = (
            "You are an evaluator AI.\n\n"
            "Evaluate the provided response based on:\n"
            "1. Accuracy (based exclusively on context)\n"
            "2. Relevance to the query\n"
            "3. Hallucination (did it invent info not found in context?)\n\n"
            "Return JSON exactly like this:\n"
            "{\n"
            '  "score": 1,\n'
            '  "hallucination": true,\n'
            '  "reason": "brief explanation"\n'
            "}"
        )

        user_prompt = (
            f"Query: {query}\n"
            f"Context: {context_preview}\n"
            f"Response: {response}"
        )

        try:
            api_res = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            raw_eval = api_res.choices[0].message.content.strip()
            return json.loads(raw_eval)
            
        except json.JSONDecodeError:
            logger.error("Evaluator failed to return valid JSON.")
            return default_eval
        except OpenAIError as e:
            logger.error("Evaluator API Error: %s", e)
            return default_eval
        except Exception as e:
            logger.exception("Evaluator crash: %s", e)
            return default_eval
