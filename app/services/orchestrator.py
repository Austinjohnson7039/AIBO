"""
orchestrator.py
───────────────
Service layer that orchestrates the Multi-Agent pipeline.
Coordinates the Manager Router with the specialized Analyst/Support Agents.
"""

from __future__ import annotations

import logging

from app.services.graph_engine import run_agentic_query
from app.memory.memory_manager import MemoryManager
from app.evaluation.evaluator import Evaluator
from app.evaluation.guardrails import Guardrails
from app.evaluation.feedback import FeedbackStore
from app.agents.analyst import AnalystAgent
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central coordinator for the AI Cafe Manager pipeline.

    Responsibilities:
    - Route incoming user queries using the ManagerAgent
    - Hand off execution to AnalystAgent or SupportAgent
    - Return a uniform, structured payload to the API layer
    """

    def __init__(self):
        """Initialise memory and evaluation layers."""
        self.memory = MemoryManager()
        
        # Safety & Evaluation Layer
        self.evaluator = Evaluator()
        self.guardrails = Guardrails()
        self.feedback = FeedbackStore()

        # Tools for grounding the Judge
        self.analyst = AnalystAgent()
        self.retriever = Retriever()
        
        # Self-Healing: Ingest if the index doesn't exist (crucial for production)
        try:
            self.retriever.load_index()
        except FileNotFoundError:
            logger.warning("FAISS index not found. Triggering autonomous ingestion protocol...")
            from app.rag.ingest import ingest_documents
            ingest_documents()
            self.retriever.load_index()

    def handle(self, query: str) -> dict:
        """
        Process the incoming query across the Multi-Agent architecture.
        
        Args:
            query: The natural language string from the user.
            
        Returns:
            A structured payload:
            {
                "query": ...,
                "routed_agent": ...,
                "answer": ...,
                "sources": [...]
            }
        """
        logger.info("Orchestrator received query: %r", query)

        # 0. Get session memory
        memory_context = self.memory.get_context(query)

        # 1. NEW: Execute query via LangGraph State Machine
        # This replaces the Manager Router and manual Execution phases.
        graph_result = run_agentic_query(query, history=memory_context)
        
        agent_answer = graph_result.get("answer", "No answer provided.")
        sources = graph_result.get("sources", [])
        
        agent_result = {
            "answer": agent_answer,
            "sources": sources
        }

        # 3. Grounding phase (Fetch context for the Judge)
        # We fetch the full DB context and a snippet of FAQ to ensure the 
        # Evaluator has the same grounding as the agent.
        db_context = self.analyst.fetch_db_context()
        faq_context = ""
        faq_results = self.retriever.search(query, top_k=2)
        if faq_results:
            faq_context = "\n=== FAQ CONTEXT ===\n" + "\n---\n".join([r.text for r in faq_results])

        # Create a comprehensive context string for the evaluator
        eval_context = f"{memory_context}\n\n{faq_context}\n\n{db_context}"

        # 4. Evaluation & Safety checks
        safety_report = self.guardrails.check(agent_answer)
        eval_report = self.evaluator.evaluate(
            query=query, 
            response=agent_answer, 
            context=eval_context
        )
        
        # 5. Determine if we show a "Fallback Refusal" or a "Confidence Warning"
        # We only REFUSE if the guardrails say it's actually unsafe (e.g., too long/looping)
        # For hallucinations or low scores, we still show the answer but with a warning.
        is_safe = safety_report["safe"]
        final_answer = agent_answer
        
        if not is_safe:
            logger.warning("Guardrails BLOCKED response: %s", safety_report["issues"])
            final_answer = "I'm sorry, I cannot confidently or safely answer that question at this time."
        elif eval_report.get("hallucination") is True:
            logger.warning(
                "Hallucination suspected (Score: %s). Proceeding with warning label.", 
                eval_report.get("score")
            )
            
        # 6. Learning/Feedback phase
        # Only store the actual conversation into conversational memory
        self.memory.store_interaction(query, final_answer)
        
        # Store execution telemetry into persistent evaluation ledger
        all_issues = safety_report["issues"]
        if not is_safe and eval_report.get("reason"):
            all_issues.append(f"Eval Flag: {eval_report.get('reason')}")
            
        self.feedback.save_feedback(
            query=query, 
            response=agent_answer, # Store the RAW attempt for offline analysis
            score=eval_report.get("score", 0), 
            issues=all_issues
        )

        return {
            "query": query,
            "routed_agent": "LangGraph: Agentic Flow",
            "response": final_answer,
            "evaluation": eval_report,
            "safe": is_safe,
            "sources": sources if is_safe else []
        }


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s | [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Quick testing block simulating a conversation where context matters
    test_queries = [
        "Do you deliver?",                   
        "Tell me a random story about an alien cafe that I didn't ask for!" # Should trigger hallucination/safety
    ]

    orchestrator = Orchestrator()

    for idx, q in enumerate(test_queries, 1):
        print(f"\n{'-'*50}")
        print(f"[{idx}] TESTING QUERY: {q}")
        
        result = orchestrator.handle(q)
        
        print("\n--- RESPONSE PAYLOAD ---")
        for k, v in result.items():
            print(f"{k}: {v}")
