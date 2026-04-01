import uuid
import json
from collections import defaultdict
from sqlalchemy.orm import Session
from app.services.forecasting_engine import forecasting_engine
from app.services.pdf_service import generate_po_pdf
from app.services.whatsapp import send_whatsapp_alert
from app.db.models import Vendor, Ingredient, PurchaseOrder, Tenant

def run_procurement_cycle(db: Session, tenant_id: int):
    """
    Executes the tenant-scoped Agentic Procurement logic.
    1. Checks forecasting runway.
    2. Identifies items with runway_days <= 2.
    3. Groups by Vendor.
    4. If Vendor item count > 3, generate PO + dispatch.
    """
    try:
        forecast_data = forecasting_engine.get_inventory_forecast(db, tenant_id)
        if "error" in forecast_data:
            return {"status": "error", "message": forecast_data["error"]}
            
        runways = forecast_data.get("runway_metrics", [])
        shopping = forecast_data.get("shopping_list", [])
        to_buy_map = {item['ingredient_name']: item['to_buy'] for item in shopping}
        
        # Rule 1: Critical items (runway <= 2.0 days)
        critical_items = [r for r in runways if r['runway_days'] <= 2.0]
        
        # Pull vendor relational mappings for this tenant
        ingredients_db = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id).all()
        vendor_map = {i.ingredient_name: i.vendor_id for i in ingredients_db}
        
        # Group by vendor
        vendor_batches = defaultdict(list)
        for item in critical_items:
            vid = vendor_map.get(item['ingredient_name'])
            if not vid: continue # Skip if no vendor mapped
            
            needed_qty = to_buy_map.get(item['ingredient_name'], 5.0)
            if needed_qty <= 0: needed_qty = 5.0
                
            vendor_batches[vid].append({
                "name": item['ingredient_name'],
                "qty": needed_qty,
                "unit": item['unit'],
                "runway": item['runway_days']
            })
            
        dispatched_count = 0
        details = []
        for vid, items in vendor_batches.items():
            # BUG FIX (BUG 11): Threshold was >3 items, meaning most single-vendor cafes
            # with <4 critical ingredients NEVER got an auto-PO dispatched.
            # Now triggers for ANY vendor with >= 1 critical item.
            if len(items) >= 1:
                vendor = db.query(Vendor).filter(Vendor.id == vid, Vendor.tenant_id == tenant_id).first()
                if not vendor: continue
                
                v_dict = {
                    "name": vendor.name, 
                    "contact_name": vendor.contact_name, 
                    "whatsapp": vendor.whatsapp_number
                }
                
                order_id = str(uuid.uuid4())[:8].upper()
                pdf_path = generate_po_pdf(v_dict, items, order_id)
                
                # Format WhatsApp
                text_msg = f"📄 *AIBO PURCHASE ORDER: #{order_id}*\n"
                text_msg += f"Supplier: {v_dict['name']}\n"
                text_msg += "Items requested:\n\n"
                for i in items:
                    text_msg += f"• {i['name']}: {i['qty']:.1f} {i['unit']}\n"
                text_msg += f"\n*AIBO Agent (Cafe ID: {tenant_id})*"
                
                send_whatsapp_alert(text_msg)
                
                # Save formal record
                new_po = PurchaseOrder(
                    tenant_id=tenant_id,
                    vendor_id=vid,
                    status="AUTO_DISPATCHED",
                    items_json=json.dumps(items)
                )
                db.add(new_po)
                dispatched_count += 1
                details.append(f"#{order_id} to {v_dict['name']}")
                
        db.commit()
        return {
            "status": "success", 
            "message": f"Procurement Cycle Complete. Dispatched {dispatched_count} orders.",
            "details": details
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

def confirm_purchase_order(db: Session, tenant_id: int, po_id: int):
    """
    Finalizes a pending Auto-Purchase, adding items to stock.
    """
    try:
        po = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == po_id, 
            PurchaseOrder.tenant_id == tenant_id
        ).first()
        
        if not po or po.status != "AUTO_DISPATCHED":
            return {"status": "error", "message": "Pending Purchase Order not found."}
            
        from app.services.stock_engine import stock_engine
        import json
        
        items = json.loads(po.items_json)
        updated_items = []
        
        for item in items:
            name = item['name']
            qty = float(item['qty'])
            
            # Use standard restock logic
            stock_engine.restock_item(db, tenant_id, name, qty)
            updated_items.append(f"{qty} {item['unit']} of {name}")
            
        po.status = "FULFILLED"
        db.commit()
        
        return {
            "status": "success", 
            "message": f"Inventory updated! Added: {', '.join(updated_items)}",
            "po_id": po_id
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"Confirmation failed: {str(e)}"}
