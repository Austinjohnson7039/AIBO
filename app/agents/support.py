"""
support.py
──────────
Support Agent — answers customer FAQs using the RAG pipeline.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.rag.generator import RAGGenerator

logger = logging.getLogger(__name__)


class SupportAgent:
    """
    Answers customer queries by retrieving relevant FAQ entries
    and generating a natural-language response.
    """

    def __init__(self, rag_generator: Optional[RAGGenerator] = None):
        """Initialise the SupportAgent wrapping the core RAG system."""
        self.rag = rag_generator or RAGGenerator()

    def answer(self, query: str, memory_context: str = "") -> dict:
        """
        Process a customer support query.
        
        Args:
            query: The user's question.
            memory_context: Formatted string of memory/history.
            
        Returns:
            A dictionary containing the 'answer' generated and the 'sources' used.
        """
        logger.info("SupportAgent processing query...")
        return self.rag.generate_answer(query, memory_context=memory_context)
