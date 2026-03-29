"""
routes.py
─────────
All API route definitions for the AI Cafe Manager.
Import this router in main.py and mount it on the FastAPI app.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.orchestrator import Orchestrator
import io

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
    
    for f in files:
        path = os.path.join(WATCH_DIR, f)
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            record_sale_op(str(row['item']), int(row['quantity']), float(row['revenue']))
            stock_engine.deduct_sale(str(row['item']), int(row['quantity']))
        
        os.rename(path, os.path.join("data/sync/archive", f"manual_{f}"))
    
    from app.db.sync import sync_to_csv
    sync_to_csv()
    return {"status": "success", "message": f"Processed {len(files)} files manually."}

from app.services.excel_parser import fuzzy_map_columns
from app.services.procurement_agent import run_procurement_cycle

@router.post("/sync/upload/excel", tags=["Sync"])
async def upload_excel_sales(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> dict:
    """Uploads Excel daily sales, updates inventory, and triggers the Procure framework autonomously."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Ensure the file is a valid Excel format.")
        
    contents = await file.read()
    try:
        raw_df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Corrupted Excel file: {str(e)}")
        
    try:
        clean_df = fuzzy_map_columns(raw_df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    processed = 0
    from app.db.ops_helpers import record_sale_op
    for _, row in clean_df.iterrows():
        try:
            item = str(row['item']).strip()
            qty = int(row['quantity'])
            rev = float(row['revenue'])
            record_sale_op(item, qty, rev)
            stock_engine.deduct_sale(item, qty)
            processed += 1
        except Exception:
            pass 
            
    # Autonomous Triggering via Background Task thread!
    background_tasks.add_task(run_procurement_cycle)
    
    return {"status": "success", "message": f"Successfully parsed {processed} transaction rows. Autonomous agent deployed in background to verify safety stock."}

@router.get("/sync/export/sales", tags=["Sync"])
async def export_sales_excel():
    """Builds a live Excel analytical report from the database and streams it to the user."""
    grocery, recipes, sales = stock_engine.load_data()
    
    if sales.empty:
        raise HTTPException(status_code=404, detail="No historical sales to export.")
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sales['date_only'] = pd.to_datetime(sales['sale_date']).dt.date
        sales.to_excel(writer, index=False, sheet_name='All Sales Logs')
        grocery.to_excel(writer, index=False, sheet_name='Live Stocks Tracker')
        
    output.seek(0)
    
    headers = {'Content-Disposition': 'attachment; filename="AIBO_Premium_Sales_Report.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

from app.db.models import Vendor
from app.db.database import SessionLocal

class VendorRequest(BaseModel):
    name: str
    contact_name: str
    whatsapp_number: str
    category: str

@router.post("/vendors/add/", tags=["Procurement"])
async def add_vendor(req: VendorRequest) -> dict:
    db = SessionLocal()
    try:
        new_v = Vendor(
            name=req.name,
            contact_name=req.contact_name,
            whatsapp_number=req.whatsapp_number,
            category=req.category
        )
        db.add(new_v)
        db.commit()
        return {"status": "success", "message": f"Partnered with {req.name}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.get("/vendors/", tags=["Procurement"])
async def list_vendors() -> dict:
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).all()
        return {"vendors": [{"id": v.id, "name": v.name, "contact": v.contact_name, "whatsapp": v.whatsapp_number, "category": v.category} for v in vendors]}
    finally:
        db.close()

@router.post("/procurement/trigger", tags=["Procurement"])
async def trigger_procurement() -> dict:
    """Manually forces AIBO to analyze burn rates and batch-send Purchase Orders."""
    result = run_procurement_cycle()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["message"])
    return result
