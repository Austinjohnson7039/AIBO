"""
graph_engine.py
───────────────
The core LangGraph state machine for the AI Cafe Manager.
This replaces the manual routing with a true agentic flow.
"""

from __future__ import annotations
import logging
from typing import Annotated, TypedDict, Union, List

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import GROQ_API_KEY
from app.agents.tools import (
    search_faq, 
    query_business_data, 
    add_new_inventory, 
    edit_inventory_item, 
    record_customer_sale,
    add_new_grocery_item,
    remove_grocery_item,
    edit_grocery_item,
    restock_grocery_item,
)

logger = logging.getLogger(__name__)

# ─── State Definition ─────────────────────────────────────────────────────────

class State(TypedDict):
    """The state of our conversation and agent reasoning."""
    # Annotate messages so that new messages are appended rather than overwritten
    messages: Annotated[list, add_messages]

# ─── Configuration ────────────────────────────────────────────────────────────

# Define the tools available to the agent
tools = [
    search_faq, 
    query_business_data, 
    add_new_inventory, 
    edit_inventory_item, 
    record_customer_sale,
    add_new_grocery_item,
    remove_grocery_item,
    edit_grocery_item,
    restock_grocery_item,
]

# Initialize the LLM with tool-calling capabilities
# BUG FIX (BUG 18): Was crashing on import if GROQ_API_KEY is empty.
# Now fails gracefully with a clear error message instead of an import crash.
if not GROQ_API_KEY:
    logger.error(
        "GROQ_API_KEY is not set. The LangGraph agent will not function. "
        "Set GROQ_API_KEY in your .env file."
    )
    llm = None
else:
    try:
        llm = ChatGroq(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            api_key=GROQ_API_KEY,
            temperature=0
        ).bind_tools(tools)
    except Exception as e:
        logger.error("Failed to initialize ChatGroq LLM: %s", e)
        llm = None

# ─── Nodes ────────────────────────────────────────────────────────────────────

def chatbot_node(state: State):
    """
    The reasoning core of the agent. 
    It evaluates the history and decides if it needs a tool or can answer.
    """
    logger.info("Graph: Executing Chatbot Node...")
    
    # Guard: if LLM failed to initialize (missing API key), return graceful error
    if llm is None:
        return {"messages": [AIMessage(content="AI service is unavailable: GROQ_API_KEY is not configured. Please set it in your .env file.")]}
    
    try:
        # 1. Standardize all messages in state to formal LangChain objects
        raw_messages = state.get("messages", [])
        formatted_messages = []
        has_system = False
        
        for m in raw_messages:
            if isinstance(m, BaseMessage):
                formatted_messages.append(m)
                if isinstance(m, SystemMessage):
                    has_system = True
            elif isinstance(m, dict):
                # Handle dictionary-style messages if they leaked in
                role = m.get("role")
                content = m.get("content", "")
                if role == "system":
                    formatted_messages.append(SystemMessage(content=content))
                    has_system = True
                elif role == "user":
                    formatted_messages.append(HumanMessage(content=content))
                elif role in ["assistant", "ai"]:
                    formatted_messages.append(AIMessage(content=content))

        # 2. Prepend System Prompt if missing
        if not has_system:
            system_msg = SystemMessage(content=(
                "You are the AI Cafe Manager. You are an expert at managing inventory, "
                "analyzing sales, and answering customer FAQs.\n\n"
                "REASONING RULES:\n"
                "1. If a user asks about policy/FAQ, use 'search_faq'.\n"
                "2. If a user asks for data (totals, counts, trends), use 'query_business_data'.\n"
                "3. If a user wants to MODIFY data (add/edit/sell), use the appropriate operation tool.\n"
                "4. You can call MULTIPLE tools in sequence if needed (e.g., check stock then add more).\n"
                "5. Be concise and professional."
            ))
            formatted_messages = [system_msg] + formatted_messages
        
        # 3. Invoke LLM with normalized list
        response = llm.invoke(formatted_messages)
        return {"messages": [response]}
        
    except Exception as e:
        logger.exception("Error in chatbot_node: %s", e)
        # Fallback message to prevent graph from stalling
        return {"messages": [AIMessage(content=f"Error in reasoning node: {e}")]}

# ─── Graph Construction ───────────────────────────────────────────────────────

# Initialize the builder
builder = StateGraph(State)

# Add our custom reasoning node
builder.add_node("chatbot", chatbot_node)

# Add the prebuilt ToolNode to handle execution of the tools list
builder.add_node("tools", ToolNode(tools))

# ─── Edges & Routing ──────────────────────────────────────────────────────────

# Start at the chatbot
builder.add_edge(START, "chatbot")

# The 'tools_condition' automatically routes to "tools" if the LLM requested a tool call,
# otherwise it routes to END.
builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

# After tools are finished, go back to the chatbot to summarize the result
builder.add_edge("tools", "chatbot")

# Compile the graph
graph = builder.compile()

# ─── Entry Point Helper ───────────────────────────────────────────────────────

def run_agentic_query(query: str, history: List = None) -> dict:
    """
    High-level entry point to invoke the LangGraph agent.
    """
    # Convert history dicts/messages into LangChain objects
    formatted_history = []
    if history:
        for m in history:
            if isinstance(m, BaseMessage):
                formatted_history.append(m)
            elif isinstance(m, dict):
                role = m.get("role")
                content = m.get("content")
                if role == "user":
                    formatted_history.append(HumanMessage(content=content))
                elif role == "assistant":
                    from langchain_core.messages import AIMessage
                    formatted_history.append(AIMessage(content=content))
                elif role == "system":
                    formatted_history.append(SystemMessage(content=content))
    
    # Add the current query
    formatted_history.append(HumanMessage(content=query))
    
    logger.info("Invoking LangGraph with query: %s", query)
    
    # Run the graph
    final_state = graph.invoke({"messages": formatted_history})
    
    last_message = final_state["messages"][-1]
    
    return {
        "answer": last_message.content,
        "history": final_state["messages"],
        "sources": ["LangGraph: Agentic Reasoning", "Tools: Database/Vector Store"]
    }
