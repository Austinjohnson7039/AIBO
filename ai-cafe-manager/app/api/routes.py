"""
routes.py
─────────
All API route definitions for the AI Cafe Manager.
Import this router in main.py and mount it on the FastAPI app.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.orchestrator import Orchestrator

# Instantiate the global orchestrator instance
orchestrator = Orchestrator()

router = APIRouter(redirect_slashes=False)

class QueryRequest(BaseModel):
    query: str

@router.get("/", tags=["Health"])
async def root() -> dict:
    """Health-check endpoint — confirms the server is running."""
    return {"message": "AI Cafe Manager Running 🚀"}

@router.post("/query/", tags=["AI"])
@router.post("/query", tags=["AI"])
async def run_query(req: QueryRequest) -> dict:
    """Orchestrator entry point evaluating queries."""
    # Defers the handling strictly to the multi-agent backend 
    return orchestrator.handle(req.query)

from app.services.stock_engine import stock_engine

@router.get("/dashboard/", tags=["Dashboard"])
async def get_dashboard() -> dict:
    """Returns analytics and alerts for the UI Dashboard."""
    return stock_engine.get_dashboard_data()

class RestockRequest(BaseModel):
    ingredient_name: str
    added_amount: float

@router.post("/grocery/restock/", tags=["Grocery"])
async def restock_grocery(req: RestockRequest) -> dict:
    """Manually add stock to an ingredient."""
    success = stock_engine.restock_item(req.ingredient_name, req.added_amount)
    if success:
        return {"status": "success", "message": f"Added {req.added_amount} to {req.ingredient_name}"}
    return {"status": "error", "message": f"Ingredient '{req.ingredient_name}' not found."}

class AddGroceryRequest(BaseModel):
    ingredient_name: str
    category: str
    unit: str
    current_stock: float
    reorder_level: float
    unit_cost_inr: float

@router.post("/grocery/add/", tags=["Grocery"])
async def add_grocery(req: AddGroceryRequest) -> dict:
    """Manually add a new grocery item to the database."""
    success, msg = stock_engine.add_grocery_item(
        req.ingredient_name, req.category, req.unit, 
        req.current_stock, req.reorder_level, req.unit_cost_inr
    )
    if success:
        return {"status": "success", "message": msg}
    return {"status": "error", "message": msg}

class RemoveGroceryRequest(BaseModel):
    ingredient_name: str

@router.delete("/grocery/remove/", tags=["Grocery"])
async def remove_grocery(req: RemoveGroceryRequest) -> dict:
    """Remove a grocery item from the database."""
    success, msg = stock_engine.remove_grocery_item(req.ingredient_name)
    if success:
        return {"status": "success", "message": msg}
    return {"status": "error", "message": msg}

from app.services.forecasting_engine import forecasting_engine

@router.get("/analytics/forecast/", tags=["Analytics"])
async def get_forecast() -> dict:
    """Returns inventory runway and smart shopping list."""
    return forecasting_engine.get_inventory_forecast()

@router.get("/analytics/trends/", tags=["Analytics"])
async def get_trends() -> dict:
    """Returns marketing insights and item momentum."""
    return forecasting_engine.get_marketing_insights()

import os
import pandas as pd
from app.db.ops_helpers import record_sale_op

@router.post("/sync/manual/", tags=["Sync"])
async def trigger_manual_sync() -> dict:
    """Manually triggers processing of any CSVs in 'incoming' folder."""
    WATCH_DIR = "data/sync/incoming"
    files = [f for f in os.listdir(WATCH_DIR) if f.endswith('.csv')]
    if not files:
        return {"status": "info", "message": "No new files to sync."}
    
    # Simple manual run of the same logic in sync_watcher
    for f in files:
        path = os.path.join(WATCH_DIR, f)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            record_sale_op(str(row['item']), int(row['quantity']), float(row['revenue']))
            stock_engine.deduct_sale(str(row['item']), int(row['quantity']))
        
        # Archive
        os.rename(path, os.path.join("data/sync/archive", f"manual_{f}"))
    
    from app.db.sync import sync_to_csv
    sync_to_csv()
    return {"status": "success", "message": f"Processed {len(files)} files manually."}
