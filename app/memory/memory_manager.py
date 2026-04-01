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
        self.short_term = ShortTermMemory(limit=10)
        self.long_term = LongTermMemory()
        self.learning = LearningRetriever()

    def get_chat_messages(self, tenant_id: int) -> List[Dict[str, str]]:
        """
        Returns structured conversation history as a list of role/content dicts
        suitable for direct injection into LangChain message lists.
        
        Returns:
            List of dicts like [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        recent = self.short_term.get_recent(tenant_id)
        messages = []
        for interaction in recent:
            messages.append({"role": "user", "content": interaction["query"]})
            messages.append({"role": "assistant", "content": interaction["response"]})
        return messages

    def get_context(self, tenant_id: int, query: str) -> str:
        """
        Retrieves recent interactions + relevant past interactions scaled to the specific tenant.
        Returns a formatted markdown string ready to be injected into an LLM prompt.
        Used for the Evaluator grounding context (NOT for the LLM conversation history).
        """
        context_blocks = []
        
        # 1. Short-term (Recent Conversation)
        recent = self.short_term.get_recent(tenant_id)
        if recent:
            context_blocks.append("--- Recent Conversation History ---")
            for interaction in recent:
                context_blocks.append(f"User: {interaction['query']}")
                context_blocks.append(f"Assistant: {interaction['response']}\n")
                
        # 2. Long-term (Relevant Past Knowledge)
        relevant_past = self.long_term.search_memory(tenant_id, query)
        if relevant_past:
            context_blocks.append("--- Relevant Past Memory ---")
            for interaction in relevant_past:
                context_blocks.append(f"Past Q: {interaction['query']}")
                context_blocks.append(f"Past A: {interaction['response']}\n")
                
        # 3. Active Learning (Golden Examples)
        expert_examples = self.learning.get_expert_examples(tenant_id, query)
        if expert_examples:
            context_blocks.append(expert_examples)

        if not context_blocks:
            return ""
            
        return "\n".join(context_blocks)

    def store_interaction(self, tenant_id: int, query: str, response: str) -> None:
        """Saves interaction to both short and long term memory storage concurrently mapped to active tenant."""
        self.short_term.add(tenant_id, query, response)
        self.long_term.save_memory(tenant_id, query, response)
