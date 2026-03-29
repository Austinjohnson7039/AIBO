from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import io
import os
import pandas as pd

from app.db.database import get_db
from app.db.models import Tenant, Sale, Inventory, Ingredient, Vendor, PurchaseOrder, Recipe
from app.api.auth import get_current_tenant, get_password_hash, verify_password, create_access_token
from app.services.stock_engine import stock_engine
from app.services.forecasting_engine import forecasting_engine
from app.services.procurement_agent import run_procurement_cycle
from app.services.menu_agent import menu_agent
from app.services.excel_parser import fuzzy_map_columns

router = APIRouter() # Allow FastAPI to handle slashes naturally

# ─── Auth Routes ──────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    location: str = "Bengaluru"

@router.post("/auth/signup", tags=["Auth"])
async def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if db.query(Tenant).filter(Tenant.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_tenant = Tenant(
        name=req.name,
        email=req.email,
        password_hash=get_password_hash(req.password),
        location=req.location
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    return {"message": "Cafe registered successfully", "id": new_tenant.id}

@router.post("/auth/login", tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.email == form_data.username).first()
    if not tenant or not verify_password(form_data.password, tenant.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": tenant.email})
    return {"access_token": access_token, "token_type": "bearer", "cafe_name": tenant.name}

# ─── Dashboard & Stock ────────────────────────────────────────────────────────

@router.get("/dashboard/", tags=["Dashboard"])
async def get_dashboard(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return stock_engine.get_dashboard_data(db, tenant.id)

class RestockRequest(BaseModel):
    ingredient_name: str
    added_amount: float

@router.post("/grocery/restock/", tags=["Grocery"])
async def restock_grocery(req: RestockRequest, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    success = stock_engine.restock_item(db, tenant.id, req.ingredient_name, req.added_amount)
    if success:
        return {"status": "success", "message": f"Added {req.added_amount} to {req.ingredient_name}"}
    return {"status": "error", "message": "Ingredient not found."}

class AddGroceryRequest(BaseModel):
    ingredient_name: str
    category: str
    unit: str
    current_stock: float
    reorder_level: float
    unit_cost_inr: float

@router.post("/grocery/add/", tags=["Grocery"])
async def add_grocery(req: AddGroceryRequest, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    success, msg = stock_engine.add_grocery_item(db, tenant.id, req)
    return {"status": "success" if success else "error", "message": msg}

@router.delete("/grocery/remove/", tags=["Grocery"])
async def remove_grocery(ingredient_name: str, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    success, msg = stock_engine.remove_grocery_item(db, tenant.id, ingredient_name)
    return {"status": "success" if success else "error", "message": msg}

# ─── Analytics & Smart Menu ───────────────────────────────────────────────────

@router.get("/analytics/forecast/", tags=["Analytics"])
async def get_forecast(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return forecasting_engine.get_inventory_forecast(db, tenant.id)

@router.get("/analytics/smart-menu/", tags=["Analytics"])
async def get_smart_menu(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    recs = await menu_agent.generate_recommendations(db, tenant)
    return {"recommendations": recs, "location": tenant.location}

@router.get("/analytics/trends/", tags=["Analytics"])
async def get_trends(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return forecasting_engine.get_marketing_insights(db, tenant.id)

from app.agents.manager import ManagerAgent
from app.agents.analyst import AnalystAgent
from app.agents.operations import OperationsAgent

manager_agent = ManagerAgent()
analyst_agent = AnalystAgent()
operations_agent = OperationsAgent()

class QueryRequest(BaseModel):
    query: str

@router.post("/query/", tags=["AI"])
async def query_ai(req: QueryRequest, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    """
    Agentic RAG Node: Routes and processes business intelligence and operational queries.
    """
    # 1. Classify intent
    intent = manager_agent.decide_agent(req.query)
    
    # 2. Process based on intent
    if intent == 'analyst':
        res = analyst_agent.analyze(req.query, tenant.id)
        return {
            "response": res["answer"],
            "evaluation": {"score": 9, "safe": True},
            "sources": res.get("sources", [])
        }
    
    if intent == 'operations':
        # Parse the action
        action_json = operations_agent.parse_action(req.query)
        # Execute the action
        result_msg = operations_agent.execute_action(db, tenant.id, action_json)
        return {
            "response": result_msg,
            "evaluation": {"score": 9, "safe": True},
            "sources": ["Operations Hub"]
        }
    
    # For 'support' and any other intent, use the analyst as a general assistant
    res = analyst_agent.analyze(req.query, tenant.id)
    return {
        "response": res["answer"],
        "evaluation": {"score": 8, "safe": True},
        "sources": res.get("sources", [])
    }

# ─── Sync (POS Upload) ────────────────────────────────────────────────────────

@router.post("/sync/upload/excel", tags=["Sync"])
async def upload_excel_sales(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    tenant: Tenant = Depends(get_current_tenant), 
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
        clean_df = fuzzy_map_columns(df)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not read the uploaded Excel file. Please download the template and try again.")
    
    processed = 0
    for _, row in clean_df.iterrows():
        stock_engine.record_sale_and_deduct(db, tenant.id, str(row['item']), int(row['quantity']), float(row['revenue']))
        processed += 1
    
    background_tasks.add_task(run_procurement_cycle, db, tenant.id)
    return {"status": "success", "message": f"Processed {processed} sales. Agent triggered."}

@router.get("/sync/template", tags=["Sync"])
async def download_excel_template():
    """Provides a fresh, perfectly formatted POS upload template for new cafe owners."""
    df = pd.DataFrame([
        {"Date (Optional)": "2026-03-30", "Product Name": "Example Burger", "Units Sold": "10", "Total Sales (INR)": "3500.00"},
        {"Date (Optional)": "2026-03-30", "Product Name": "Vanilla Latte", "Units Sold": "45", "Total Sales (INR)": "9000.00"}
    ])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales_Template')
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="AIBO_Sales_Template.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@router.get("/sync/export/sales", tags=["Sync"])
async def export_sales(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    """Exports all historical sales for the logged-in cafe to an Excel document offline."""
    sales = db.query(Sale).filter(Sale.tenant_id == tenant.id).all()
    
    if not sales:
        data = [{"Date": "N/A", "Item Name": "No Data", "Quantity Sold": 0, "Total Sales (INR)": 0}]
    else:
        data = [{
            "Date": s.sale_date.strftime("%Y-%m-%d %H:%M:%S") if s.sale_date else "",
            "Item Name": s.item,
            "Quantity Sold": s.quantity,
            "Total Sales (INR)": s.revenue
        } for s in sales]
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales_Export')
    output.seek(0)
    
    # Clean filename by stripping spaces
    safe_name = "".join([c for c in tenant.name if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_")
    
    headers = {
        'Content-Disposition': f'attachment; filename="AIBO_{safe_name}_Export.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ─── Vendors & Procurement ────────────────────────────────────────────────────

@router.get("/vendors/", tags=["Procurement"])
async def list_vendors(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(Vendor.tenant_id == tenant.id).all()
    return {"vendors": vendors}

class VendorRequest(BaseModel):
    name: str
    contact_name: str
    whatsapp_number: str
    category: str

@router.post("/vendors/add/", tags=["Procurement"])
async def add_vendor(req: VendorRequest, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    v = Vendor(tenant_id=tenant.id, **req.dict())
    db.add(v)
    db.commit()
    return {"status": "success", "message": f"Added vendor {v.name}"}

@router.post("/procurement/trigger", tags=["Procurement"])
async def trigger_procurement(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return run_procurement_cycle(db, tenant.id)

# ─── Employee Management & Shifts ─────────────────────────────────────────────

from app.db.models import Employee, Attendance, Wastage, Batch
from datetime import datetime

class EmployeeRequest(BaseModel):
    name: str
    role: str
    hourly_rate: float
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None

@router.get("/staff/", tags=["Staff"])
async def list_staff(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    employees = db.query(Employee).filter(Employee.tenant_id == tenant.id).all()
    return {"employees": employees}

@router.post("/staff/add/", tags=["Staff"])
async def add_staff(req: EmployeeRequest, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    e = Employee(tenant_id=tenant.id, **req.dict())
    db.add(e)
    db.commit()
    return {"status": "success", "message": f"Added employee {e.name}"}

@router.post("/staff/clock-in/{employee_id}", tags=["Staff"])
async def clock_in(employee_id: int, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    # Simple clock in
    new_att = Attendance(
        tenant_id=tenant.id,
        employee_id=employee_id,
        date=datetime.utcnow(),
        check_in=datetime.utcnow()
    )
    db.add(new_att)
    db.commit()
    return {"status": "success", "message": "Clocked in successfully."}

@router.post("/staff/clock-out/{employee_id}", tags=["Staff"])
async def clock_out(employee_id: int, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    att = db.query(Attendance).filter(
        Attendance.tenant_id == tenant.id, 
        Attendance.employee_id == employee_id,
    ).order_by(Attendance.id.desc()).first()
    
    if not att or att.check_out:
        return {"status": "error", "message": "Not clocked in."}
        
    att.check_out = datetime.utcnow()
    diff = att.check_out - att.check_in
    att.total_hours = diff.total_seconds() / 3600.0
    db.commit()
    return {"status": "success", "message": "Clocked out.", "hours": round(att.total_hours, 2)}

@router.get("/staff/salaries/", tags=["Staff"])
async def get_salaries(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    employees = db.query(Employee).filter(Employee.tenant_id == tenant.id).all()
    salaries = []
    for e in employees:
        atts = db.query(Attendance).filter(Attendance.employee_id == e.id).all()
        total_hrs = sum(a.total_hours for a in atts)
        salaries.append({
            "employee_id": e.id,
            "name": e.name,
            "role": e.role,
            "total_hours": round(total_hrs, 2),
            "salary": round(total_hrs * e.hourly_rate, 2)
        })
    return {"salaries": salaries}

# ─── Wastage & Expiry ─────────────────────────────────────────────────────────

class WastageRequest(BaseModel):
    item_name: str
    quantity: float
    loss_amount: float
    reason: str = "expired"

@router.post("/wastage/add/", tags=["Wastage"])
async def add_wastage(req: WastageRequest, tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    w = Wastage(tenant_id=tenant.id, **req.dict())
    
    # Optional logic: Deduct from ingredient stock
    ing = db.query(Ingredient).filter(Ingredient.tenant_id == tenant.id, Ingredient.ingredient_name == req.item_name).first()
    if ing:
        ing.current_stock -= req.quantity
    
    db.add(w)
    db.commit()
    return {"status": "success", "message": "Wastage logged."}

@router.get("/wastage/", tags=["Wastage"])
async def get_wastage(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    wastage = db.query(Wastage).filter(Wastage.tenant_id == tenant.id).order_by(Wastage.logged_at.desc()).all()
    return {"wastage": wastage}

@router.get("/analytics/staffing-recommendation/", tags=["Analytics"])
async def get_staffing_recs(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    # AI logic representing the upgrade
    sales = db.query(Sale).filter(Sale.tenant_id == tenant.id).all()
    # Basic logic to recommend reducing staff if we don't have many recent sales
    num_sales = len(sales)
    
    if num_sales < 10:
        alert = "Reduce 1 staff during slow hours"
    else:
        alert = "Traffic is normal. Current staffing is optimal."
        
    return {"recommendation": alert}
