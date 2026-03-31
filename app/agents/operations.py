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

from app.services.stock_engine import stock_engine
from sqlalchemy.orm import Session
from app.db.models import Ingredient # Grocery items

class OperationsAgent:
    """
    Parses "Action Intents" (Add/Update/Record) into structured JSON payloads
    and executes them against the tenant's database.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialise the OperationsAgent with an OpenAI client."""
        key = api_key or GROQ_API_KEY
        if key:
            self.client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)
        else:
            self.client = None

    def execute_action(self, db: Session, tenant_id: int, action_json: Dict[str, Any]) -> str:
        """
        Takes a parsed action JSON and performs the database operation.
        """
        action = action_json.get("action")
        item_name = action_json.get("item_name")
        qty = action_json.get("quantity", 0)
        
        try:
            if action == 'add_inventory':
                # Check if it was meant for 'Grocery' (Ingredient table)
                # First, try to restock existing
                success = stock_engine.restock_item(db, tenant_id, item_name, float(qty))
                if success:
                    return f"Successfully added {qty} units to '{item_name}' in your Grocery Hub."
                
                # If not found, create new grocery item
                # AI might not have provided all fields, use defaults
                from app.db.models import Ingredient
                new_ing = Ingredient(
                    tenant_id=tenant_id,
                    ingredient_name=item_name,
                    category=action_json.get("category", "General"),
                    current_stock=float(qty),
                    unit="pcs",
                    reorder_level=10.0,
                    unit_cost_inr=0.0
                )
                db.add(new_ing)
                db.commit()
                return f"Registered new ingredient '{item_name}' with {qty} units in your Grocery Hub."

            elif action == 'record_sale':
                rev = action_json.get("revenue", 0.0)
                stock_engine.record_sale_and_deduct(db, tenant_id, item_name, int(qty), float(rev))
                return f"Sale recorded: {qty}x {item_name} for ₹{rev}. Stock has been intelligently deducted."

            elif action == 'record_wastage':
                loss = action_json.get("loss_amount", 0.0)
                reason = action_json.get("reason", "expired")
                # Deduct inventory
                from app.db.models import Wastage, Ingredient
                ing = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id, Ingredient.ingredient_name == item_name).first()
                if ing:
                    ing.current_stock = max(0.0, float(ing.current_stock) - float(qty))
                
                w = Wastage(tenant_id=tenant_id, item_name=item_name, quantity=float(qty), loss_amount=float(loss), reason=reason)
                db.add(w)
                db.commit()
                return f"Wastage recorded: {qty}x {item_name} ({reason}) for a loss of ₹{loss}."

            elif action == 'update_inventory':
                updates = action_json.get("updates", {})
                if not updates:
                    return "No distinct update fields provided. Please specify what you want changed."
                
                # 1. Try Menu Inventory first
                from app.db.ops_helpers import update_inventory_op
                if update_inventory_op(tenant_id, item_name, updates):
                    return f"Successfully updated '{item_name}' in your active menu."
                
                # 2. Try Grocery Ingredients
                ing = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id, Ingredient.ingredient_name.like(f"%{item_name}%")).first()
                if ing:
                    for field, value in updates.items():
                        if hasattr(ing, field) and value is not None:
                            setattr(ing, field, value)
                    db.commit()
                    return f"Successfully updated your raw grocery stock for '{item_name}'."
                
                return f"Could not locate '{item_name}' in either menu catalogue or grocery stock."

            elif action == 'ask_clarification':
                return action_json.get("clarification_msg", "I need more details to perform that action.")

            return "I understood the request but I'm unsure how to execute that specific action yet."

        except Exception as e:
            logger.error("Execution error: %s", e)
            return f"I encountered an error while updating your records: {str(e)}"

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
            "3. 'record_wastage': User wants to log expired or wasted items.\n"
            "   - REQUIRED: 'item_name', 'quantity', 'loss_amount', 'reason' (e.g. 'expired').\n"
            "4. 'update_inventory': User wants to EDIT or SET specific existing fields (overwrite values).\n"
            "   - Keywords: 'set', 'change', 'update', 'edit'.\n"
            "   - Example: 'Set stock of brownie to 100' or 'Change price of coffee to 5'.\n"
            "   - REQUIRED: 'item_name', 'updates' (dictionary of fields and their NEW absolute values).\n"
            "   - VALID fields for updates: 'stock', 'reorder_level', 'category', 'item_type', 'unit', 'cost_price', 'selling_price', 'supplier'.\n"
            "5. 'ask_clarification': If any REQUIRED fields are missing.\n\n"
            "OUTPUT FORMAT: ONLY return raw JSON matching: \n"
            '{"action": "...", "item_name": "...", "quantity": ..., "revenue": ..., "loss_amount": ..., "reason": "...", "reorder_level": ..., "category": "...", "updates": {...}, "clarification_msg": "..."}\n'
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
