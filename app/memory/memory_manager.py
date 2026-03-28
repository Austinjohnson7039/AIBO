"""
memory_manager.py
─────────────────
Combines the short-term and long-term memory systems to provide 
formatted context strings for the agents.
"""

import logging
from typing import List, Dict

from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory
from app.memory.learning import LearningRetriever

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Facade managing both ephemeral session context and persistent long term knowledge.
    """

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.learning = LearningRetriever()

    def get_context(self, query: str) -> str:
        """
        Retrieves recent interactions + relevant past interactions.
        Returns a formatted markdown string ready to be injected into an LLM prompt.
        """
        context_blocks = []
        
        # 1. Short-term (Recent Conversation)
        recent = self.short_term.get_recent()
        if recent:
            context_blocks.append("--- Recent Conversation History ---")
            for interaction in recent:
                context_blocks.append(f"User: {interaction['query']}")
                context_blocks.append(f"Assistant: {interaction['response']}\n")
                
        # 2. Long-term (Relevant Past Knowledge)
        relevant_past = self.long_term.search_memory(query)
        if relevant_past:
            context_blocks.append("--- Relevant Past Memory ---")
            for interaction in relevant_past:
                context_blocks.append(f"Past Q: {interaction['query']}")
                context_blocks.append(f"Past A: {interaction['response']}\n")
                
        # 3. Active Learning (Golden Examples)
        expert_examples = self.learning.get_expert_examples(query)
        if expert_examples:
            context_blocks.append(expert_examples)

        if not context_blocks:
            return ""
            
        return "\n".join(context_blocks)

    def store_interaction(self, query: str, response: str) -> None:
        """Saves interaction to both short and long term memory storage concurrently."""
        self.short_term.add(query, response)
        self.long_term.save_memory(query, response)
