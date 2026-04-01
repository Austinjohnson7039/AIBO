"""
orchestrator.py
───────────────
Service layer that orchestrates the Multi-Agent pipeline.
Coordinates the Manager Router with the specialized Analyst/Support Agents.
Now includes: chat memory fix, pre-LLM guardrails, and thinking transparency.
"""

from __future__ import annotations

import logging
import time

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
    - Screen input for off-topic / jailbreak attempts (guardrails)
    - Route incoming user queries using the LangGraph agent
    - Inject proper conversation history for context continuity
    - Capture transparent "thinking" steps (sanitized for user display)
    - Evaluate and score responses
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
        
        # Self-Healing: Trigger autonomous ingestion if index is missing (common on first deploy)
        try:
            self.retriever.load_index()
        except FileNotFoundError:
            logger.warning("FAISS index not found. Triggering autonomous ingestion protocol...")
            from app.rag.ingest import ingest_documents
            try:
                ingest_documents()
                self.retriever.load_index()
                logger.info("Autonomous ingestion successful.")
            except Exception as e:
                logger.error("Failed to recover FAISS index: %s", e)

    def handle(self, tenant_id: int, query: str) -> dict:
        """
        Process the incoming query across the Multi-Agent architecture.
        
        Args:
            tenant_id: The active session owner ID.
            query: The natural language string from the user.
            
        Returns:
            A structured payload with response, evaluation, safety, sources, and thinking steps.
        """
        logger.info("Orchestrator received query: %r", query)
        thinking = []
        start_time = time.time()

        # ──────────────────────────────────────────────────────────────────
        # STEP 0: Pre-LLM Input Guardrails
        # ──────────────────────────────────────────────────────────────────
        thinking.append({
            "step": "Input Screening",
            "icon": "🛡️",
            "detail": "Checking query against safety guardrails and topic filters..."
        })

        input_check = self.guardrails.check_input(query)
        
        if not input_check["allowed"]:
            thinking.append({
                "step": "Guardrail Triggered",
                "icon": "🚫",
                "detail": f"Query was blocked: {input_check['reason']}. Returning cafe-focused response."
            })
            
            # Store the blocked interaction for analytics
            refusal_msg = input_check["refusal_message"]
            self.memory.store_interaction(tenant_id, query, refusal_msg)
            self.feedback.save_feedback(
                tenant_id=tenant_id,
                query=query,
                response=refusal_msg,
                score=0,
                issues=[f"BLOCKED: {input_check['reason']}"]
            )
            
            elapsed = round(time.time() - start_time, 2)
            thinking.append({
                "step": "Complete",
                "icon": "✅",
                "detail": f"Guardrail response served in {elapsed}s."
            })
            
            return {
                "query": query,
                "routed_agent": "Guardrails: Pre-LLM Filter",
                "response": refusal_msg,
                "evaluation": {"score": 10, "hallucination": False, "reason": "Guardrail refusal — no hallucination possible."},
                "safe": True,
                "sources": [],
                "thinking": thinking
            }

        thinking[-1]["detail"] = "All guardrail checks passed ✓"

        # ──────────────────────────────────────────────────────────────────
        # STEP 1: Retrieve Conversation History
        # ──────────────────────────────────────────────────────────────────
        chat_messages = self.memory.get_chat_messages(tenant_id)
        memory_context = self.memory.get_context(tenant_id, query)
        
        msg_count = len(chat_messages) // 2  # Each exchange is 2 messages
        thinking.append({
            "step": "Memory Retrieval",
            "icon": "🧠",
            "detail": f"Loaded {msg_count} previous conversation exchanges for context continuity."
        })

        # ──────────────────────────────────────────────────────────────────
        # STEP 2: Execute via LangGraph Agentic Flow
        # ──────────────────────────────────────────────────────────────────
        thinking.append({
            "step": "Agent Reasoning",
            "icon": "⚡",
            "detail": "Invoking LangGraph state machine with tool access to databases, FAQ, and operations..."
        })

        # Secure Context Thread Delegation
        from app.agents.tools import tenant_context
        tenant_context.set(tenant_id)
        
        # Pass structured chat messages (not raw string) for proper LLM history
        graph_result = run_agentic_query(query, history=chat_messages)
        
        agent_answer = graph_result.get("answer", "No answer provided.")
        sources = graph_result.get("sources", [])
        
        # Analyze tool calls from the graph execution for thinking transparency
        graph_messages = graph_result.get("history", [])
        tools_used = []
        for msg in graph_messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                    tools_used.append(tool_name)
        
        if tools_used:
            # Map internal tool names to user-friendly descriptions
            tool_labels = {
                "search_faq": "Searched cafe policies & FAQ",
                "query_business_data": "Queried business analytics database",
                "add_new_inventory": "Added item to menu inventory",
                "edit_inventory_item": "Updated menu item details",
                "record_customer_sale": "Recorded a customer sale",
                "add_new_grocery_item": "Added new grocery ingredient",
                "remove_grocery_item": "Removed a grocery ingredient",
                "edit_grocery_item": "Edited grocery ingredient details",
                "restock_grocery_item": "Restocked a grocery ingredient",
            }
            friendly_tools = [tool_labels.get(t, f"Executed: {t}") for t in tools_used]
            thinking.append({
                "step": "Tools Used",
                "icon": "🔧",
                "detail": " → ".join(friendly_tools)
            })
        else:
            thinking.append({
                "step": "Direct Response",
                "icon": "💬",
                "detail": "Answered directly from conversation context (no database lookup needed)."
            })

        # ──────────────────────────────────────────────────────────────────
        # STEP 3: Grounding & Evaluation
        # ──────────────────────────────────────────────────────────────────
        thinking.append({
            "step": "Quality Check",
            "icon": "⚖️",
            "detail": "Running AI Judge to evaluate accuracy and detect hallucinations..."
        })

        db_context = self.analyst.fetch_db_context(tenant_id)
        faq_context = ""
        faq_results = self.retriever.search(query, top_k=2)
        if faq_results:
            faq_context = "\n=== FAQ CONTEXT ===\n" + "\n---\n".join([r.text for r in faq_results])

        eval_context = f"{memory_context}\n\n{faq_context}\n\n{db_context}"

        # Safety & Evaluation
        safety_report = self.guardrails.check(agent_answer)
        eval_report = self.evaluator.evaluate(
            query=query, 
            response=agent_answer, 
            context=eval_context
        )
        
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
            
        eval_score = eval_report.get("score", 5)
        thinking[-1]["detail"] = f"Accuracy Score: {eval_score}/10 | Hallucination: {'Detected ⚠️' if eval_report.get('hallucination') else 'None ✓'}"

        # ──────────────────────────────────────────────────────────────────
        # STEP 4: Store & Return
        # ──────────────────────────────────────────────────────────────────
        self.memory.store_interaction(tenant_id, query, final_answer)
        
        all_issues = safety_report["issues"]
        if not is_safe and eval_report.get("reason"):
            all_issues.append(f"Eval Flag: {eval_report.get('reason')}")
            
        self.feedback.save_feedback(
            tenant_id=tenant_id,
            query=query, 
            response=agent_answer,
            score=eval_report.get("score", 0), 
            issues=all_issues
        )

        elapsed = round(time.time() - start_time, 2)
        thinking.append({
            "step": "Complete",
            "icon": "✅",
            "detail": f"Response generated in {elapsed}s. Saved to memory for future context."
        })

        return {
            "query": query,
            "routed_agent": "LangGraph: Agentic Flow",
            "response": final_answer,
            "evaluation": eval_report,
            "safe": is_safe,
            "sources": sources if is_safe else [],
            "thinking": thinking
        }
