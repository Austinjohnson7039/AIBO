"""
operations.py
─────────────
Operations Agent — handles requests to modify data (add inventory, record sales).
Parses natural language into structured action payloads.
If information is missing, it intelligently asks for clarification.
"""

from __future__ import annotations
import logging
import json
from typing import Optional, Dict, Any
from openai import OpenAI, OpenAIError
from app.config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ─── Operations ───────────────────────────────────────────────────────────────

class OperationsAgent:
    """
    Parses "Action Intents" (Add/Update/Record) into structured JSON payloads.
    It can intelligently identify missing information and prompt the user.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialise the OperationsAgent with an OpenAI client."""
        key = api_key or GROQ_API_KEY
        if key:
            self.client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)
        else:
            self.client = None

    def parse_action(self, query: str, context: str = "") -> Dict[str, Any]:
        """
        Parses the query into a structured JSON action.
        
        Expected JSON Schema:
        {
            "action": "add_inventory" | "record_sale" | "ask_clarification" | "update_inventory",
            "item_name": "string",
            "quantity": int (for add_inventory or record_sale),
            "revenue": float (for sales),
            "reorder_level": int (for add_inventory),
            "category": "string (for add_inventory)",
            "updates": { "field_name": "value" } (for update_inventory - e.g., {"stock": 100, "selling_price": 5.0}),
            "clarification_msg": "string (if action is ask_clarification)"
        }
        """
        logger.info("OperationsAgent parsing action intent...")
        
        if not self.client:
            return {"action": "error", "clarification_msg": "OperationsAgent lacks API Key."}

        system_prompt = (
            "You are a Business Operations AI for a cafe.\n"
            "Your job is to parse the user's request to MODIFY data into a structured JSON action.\n\n"
            "IMPORTANT: Resolving context. If the user's latest 'Query' is just a value (like '50', 'pcs', or 'Burger'), "
            "you MUST look at the 'Existing Context' (Conversation History) to find the 'Action' and 'item_name' "
            "they were previously discussing. \n\n"
            "ACTIONS:\n"
            "1. 'add_inventory': User wants to add INCREMENTAL stock or create a new inventory item.\n"
            "   - REQUIRED: 'item_name', 'quantity' (the amount to ADD).\n"
            "2. 'record_sale': User wants to log a new sales transaction.\n"
            "   - REQUIRED: 'item_name', 'quantity', 'revenue'.\n"
            "3. 'update_inventory': User wants to EDIT or SET specific existing fields (overwrite values).\n"
            "   - Keywords: 'set', 'change', 'update', 'edit'.\n"
            "   - Example: 'Set stock of brownie to 100' or 'Change price of coffee to 5'.\n"
            "   - REQUIRED: 'item_name', 'updates' (dictionary of fields and their NEW absolute values).\n"
            "   - VALID fields for updates: 'stock', 'reorder_level', 'category', 'item_type', 'unit', 'cost_price', 'selling_price', 'supplier'.\n"
            "4. 'ask_clarification': If any REQUIRED fields are missing.\n\n"
            "OUTPUT FORMAT: ONLY return raw JSON matching: \n"
            '{"action": "...", "item_name": "...", "quantity": ..., "revenue": ..., "reorder_level": ..., "category": "...", "updates": {...}, "clarification_msg": "..."}\n'
            "If 'action' is 'ask_clarification', use 'clarification_msg' to politely ask for the missing field."
        )

        user_prompt = f"Query: {query}\n\nExisting Context:\n{context}"

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            raw_payload = response.choices[0].message.content.strip()
            return json.loads(raw_payload)
            
        except (Exception, OpenAIError) as e:
            logger.error("OperationsAgent parse error: %s", e)
            return {"action": "error", "clarification_msg": "I encountered an error parsing your request."}
