import uuid
import json
from collections import defaultdict
from app.services.forecasting_engine import forecasting_engine
from app.services.pdf_service import generate_po_pdf
from app.services.whatsapp import send_whatsapp_alert
from app.db.database import SessionLocal
from app.db.models import Vendor, Ingredient, PurchaseOrder

def run_procurement_cycle():
    """
    Executes the Agentic Procurement logic based on the approved batching rules.
    1. Checks forecasting runway.
    2. Identifies items with runway_days <= 2.
    3. Groups by Vendor.
    4. If Vendor item count > 3, generate PO + dispatch.
    """
    db = SessionLocal()
    try:
        forecast_data = forecasting_engine.get_inventory_forecast()
        if "error" in forecast_data:
            return {"status": "error", "message": forecast_data["error"]}
            
        runways = forecast_data.get("runway_metrics", [])
        shopping = forecast_data.get("shopping_list", [])
        
        # Build lookup for predicted optimum purchase quantities
        to_buy_map = {item['ingredient_name']: item['to_buy'] for item in shopping}
        
        # Rule 1: Critical items (runway <= 2.0 days)
        critical_items = [r for r in runways if r['runway_days'] <= 2.0]
        
        # Pull vendor relational mappings
        ingredients_db = db.query(Ingredient).all()
        vendor_map = {i.ingredient_name: i.vendor_id for i in ingredients_db}
        
        # Group by vendor
        vendor_batches = defaultdict(list)
        for item in critical_items:
            # Map to vendor (Default to Vendor ID 1 if not explicitly mapped for MVP fallback)
            vid = vendor_map.get(item['ingredient_name']) or 1 
            needed_qty = to_buy_map.get(item['ingredient_name'], 10.0)
            
            # Use raw stock if to_buy is technically 0 but runway is critical
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
            # Rule 2: Smart Batching > 3 items
            if len(items) > 3:
                # Trigger Autonomous Order
                vendor = db.query(Vendor).filter(Vendor.id == vid).first()
                v_dict = {
                    "name": vendor.name if vendor else "General Supplier", 
                    "contact_name": vendor.contact_name if vendor else "Sales Team", 
                    "whatsapp": vendor.whatsapp_number if vendor else None
                }
                
                order_id = str(uuid.uuid4())[:8].upper()
                pdf_path = generate_po_pdf(v_dict, items, order_id)
                
                # Format WhatsApp Vendor Dispatch Text
                text_msg = f"📄 *AIBO PURCHASE ORDER: #{order_id}*\n"
                text_msg += f"Attention: {v_dict.get('name')}\n"
                text_msg += "Please process the following restock immediately:\n\n"
                for i in items:
                    text_msg += f"• {i['name']}: {i['qty']:.1f} {i['unit']}\n"
                
                text_msg += f"\n*AIBO Procurement Agent*\n(Authorized PDF attached in system record)"
                
                # Send order over WhatsApp interface
                # Note: Currently routes to the Admin WhatsApp number since Twilio Sandbox restricts arbitrary outbound without opt-in.
                send_whatsapp_alert(text_msg)
                
                # Save formal record to DB
                new_po = PurchaseOrder(
                    vendor_id=vid,
                    status="AUTO_DISPATCHED",
                    items_json=json.dumps(items)
                )
                db.add(new_po)
                dispatched_count += 1
                details.append(f"#{order_id} to {v_dict['name']} ({len(items)} items)")
                
        db.commit()
        return {
            "status": "success", 
            "message": f"Procurement Cycle Complete. Dispatched {dispatched_count} vendor orders.",
            "details": details
        }
    finally:
        db.close()
