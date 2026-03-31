"""
tools.py
────────
LangChain Tool definitions for the AI Cafe Manager.
These allow the LangGraph agent to interact with the Database and FAISS.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from langchain.tools import tool
from app.db.ops_helpers import add_inventory_op, record_sale_op, update_inventory_op
from app.agents.analyst import AnalystAgent
import contextvars
from app.rag.retriever import Retriever

current_tenant_id = contextvars.ContextVar("current_tenant_id", default=None)
# BUG FIX: Alias exported as `tenant_context` so orchestrator.py can do:
# `from app.agents.tools import tenant_context; tenant_context.set(tenant_id)`
tenant_context = current_tenant_id

# Initialize logic sources
analyst = AnalystAgent()
retriever = Retriever()
# LAZY LOAD index explicitly inside the tools if/when needed so it doesn't crash FastAPI on boot


@tool
def search_faq(query: str) -> str:
    """
    Search the Cafe's FAQ and policy database for answers about delivery, 
    opening hours, or general cafe policies.
    """
    try:
        if not retriever.is_loaded:
            retriever.load_index()
    except Exception:
        pass
        
    if not retriever.is_loaded:
        return "No internal FAQ entries or policies found. The knowledge base is currently empty."
        
    results = retriever.search(query, top_k=3)
    if not results:
        return "No relevant FAQ entries found."
    
    formatted = "\n---\n".join([f"Source: {r.text}" for r in results])
    return f"Retrieved Knowledge:\n{formatted}"

@tool
def query_business_data(query: str) -> str:
    """
    Query the SQL-like database for sales trends, inventory stock levels, 
    profit margins, or historical patterns. 
    Examples: 'How many brownies?', 'Total revenue yesterday?'
    """
    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution (No Tenant ID)"
    result = analyst.analyze(query, t_id)
    return result.get("answer", "No data found for that query.")

@tool
def add_new_inventory(item_name: str, quantity: int, reorder_level: int = 10, category: str = "Uncategorized") -> str:
    """
    Use this strictly for the CUSTOMER-FACING MENU (e.g. "FBC Chicken Burger", "Fries", "Smoothie").
    DO NOT use this for raw grocery ingredients (like Buns, Chicken, or Lettuce).
    Add INCREMENTAL stock to an item or register a new product in the system.
    """
    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution"
    
    success = add_inventory_op(t_id, item_name, quantity, reorder_level, category)
    if success:
        return f"Successfully added {quantity} x '{item_name}' to inventory."
    return f"Failed to add inventory for '{item_name}'."

@tool
def edit_inventory_item(item_name: str, stock: Optional[int] = None, selling_price: Optional[float] = None, reorder_level: Optional[int] = None) -> str:
    """
    Use this strictly for the CUSTOMER-FACING MENU (e.g. "FBC Chicken Burger", "Fries", "Smoothie").
    DO NOT use this for raw grocery ingredients (like Buns, Chicken, or Lettuce).
    Change or set absolute values for an existing inventory item.
    """
    updates = {}
    if stock is not None: updates["stock"] = stock
    if selling_price is not None: updates["selling_price"] = selling_price
    if reorder_level is not None: updates["reorder_level"] = reorder_level
    
    if not updates:
        return "No updates provided."
        
    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution"
        
    success = update_inventory_op(t_id, item_name, updates)
    if success:
        return f"Successfully updated {item_name} with: {updates}"
    return f"Could not find item '{item_name}' to update."

@tool
def record_customer_sale(item_name: str, quantity: str, total_price: str = "0") -> str:
    """
    Log a new customer purchase and deduct stock from inventory.
    Accepts item_name, quantity, and total_price (can be passed as strings).
    """
    try:
        qty = int(quantity)
        price = float(total_price)
    except ValueError:
        return f"Error: quantity ('{quantity}') and total_price ('{total_price}') must be numbers."

    # If price is 0, try to lookup from inventory for convenience
    if price == 0:
        from app.db.database import SessionLocal
        from app.db.models import Inventory
        db = SessionLocal()
        t_id = current_tenant_id.get()
        try:
            inv_item = db.query(Inventory).filter(Inventory.tenant_id == t_id, Inventory.item_name.like(f"%{item_name}%")).first()
            if inv_item and inv_item.selling_price > 0:
                price = inv_item.selling_price * qty
        finally:
            db.close()

    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution"

    # BUG FIX: Was calling record_sale_op() (which inserts a Sale row) AND then
    # stock_engine.record_sale_and_deduct() (which inserts ANOTHER Sale row).
    # Now we use only one path: stock_engine handles recording + ingredient deduction.
    from app.services.stock_engine import stock_engine
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        stock_engine.record_sale_and_deduct(db, t_id, item_name, qty, price)
        return f"Sale successfully recorded: {qty} x '{item_name}' for ₹{price}."
    except Exception as e:
        return f"Failed to record sale for '{item_name}': {e}"
    finally:
        db.close()

@tool
def add_new_grocery_item(ingredient_name: str, category: str, unit: str, current_stock: str, reorder_level: str, unit_cost_inr: str) -> str:
    """
    Use this EXCLUSIVELY for RAW INGREDIENTS and GROCERIES (e.g., "Burger Bun", "Chicken Breast", "Lettuce", "Oil").
    DO NOT use this for full menu items.
    Add an ENTIRELY NEW raw ingredient to the Grocery Stock database.
    """
    from app.services.stock_engine import stock_engine
    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution"
    try:
        c_stock = float(current_stock)
        r_level = float(reorder_level)
        u_cost = float(unit_cost_inr)
    except ValueError:
        return "Failed to parsed numerical arguments (current_stock, reorder_level, unit_cost_inr). Ensure they are numbers."
        
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        class DummyReq:
            def __init__(self):
                self.ingredient_name = ingredient_name
                self.category = category
                self.unit = unit
                self.current_stock = c_stock
                self.reorder_level = r_level
                self.unit_cost_inr = u_cost
            def dict(self):
                return self.__dict__
                
        success, msg = stock_engine.add_grocery_item(db, t_id, DummyReq())
        return msg
    finally:
        db.close()

@tool
def remove_grocery_item(ingredient_name: str) -> str:
    """
    Use this EXCLUSIVELY for RAW INGREDIENTS and GROCERIES (e.g., "Burger Bun", "Chicken Breast", "Lettuce").
    Remove an existing raw ingredient from the Grocery Stock.
    """
    from app.services.stock_engine import stock_engine
    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution"
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        success, msg = stock_engine.remove_grocery_item(db, t_id, ingredient_name)
        return msg
    finally:
        db.close()

from typing import Optional

@tool
def edit_grocery_item(
    ingredient_name: str, 
    new_name: Optional[str] = None, 
    category: Optional[str] = None, 
    unit: Optional[str] = None, 
    current_stock: Optional[str] = None, 
    reorder_level: Optional[str] = None, 
    unit_cost_inr: Optional[str] = None
) -> str:
    """
    Use this EXCLUSIVELY for RAW INGREDIENTS and GROCERIES (e.g., "Burger Bun", "Chicken Breast").
    Edit properties (like name, cost, category) of an existing grocery item.
    """
    from app.services.stock_engine import stock_engine
    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution"
    
    kwargs = {}
    if new_name is not None: kwargs["ingredient_name"] = new_name
    if category is not None: kwargs["category"] = category
    if unit is not None: kwargs["unit"] = unit
    try:
        if current_stock is not None: kwargs["current_stock"] = float(current_stock)
        if reorder_level is not None: kwargs["reorder_level"] = float(reorder_level)
        if unit_cost_inr is not None: kwargs["unit_cost_inr"] = float(unit_cost_inr)
    except ValueError:
        return "Failed to parsed numerical arguments (current_stock, reorder_level, unit_cost_inr)."
    
    # We would theoretically update the ingredient via db session, but this tool
    # is complex and usually requires custom logic.
    from app.db.database import SessionLocal
    from app.db.models import Ingredient
    db = SessionLocal()
    try:
        ing = db.query(Ingredient).filter(Ingredient.tenant_id == t_id, Ingredient.ingredient_name == ingredient_name).first()
        if not ing:
            return "Item not found."
        for k, v in kwargs.items():
            setattr(ing, k, v)
        db.commit()
    finally:
        db.close()
    
    return f"Updated {ingredient_name}."

@tool
def restock_grocery_item(ingredient_name: str, added_amount: str) -> str:
    """
    Use this EXCLUSIVELY for RAW INGREDIENTS and GROCERIES (e.g., "Burger Bun", "Chicken Breast", "Lettuce").
    Use this to ADD or RESTOCK the quantity of an existing grocery item.
    For example: "add 20 burger buns to groceries" -> restock_grocery_item("Burger Bun", "20")
    """
    from app.services.stock_engine import stock_engine
    t_id = current_tenant_id.get()
    if not t_id: return "Error: Unauthorized Tool Execution"
    try:
        amt = float(added_amount)
    except ValueError:
        return "added_amount must be a number."
        
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        success = stock_engine.restock_item(db, t_id, ingredient_name, amt)
        if success:
            return f"Successfully restocked {ingredient_name} by adding {amt}."
        return f"Failed to restock '{ingredient_name}'. Ingredient might not exist."
    finally:
        db.close()
