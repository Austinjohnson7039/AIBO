import os
import sqlalchemy
from sqlalchemy import text

# Database URL from .env (Hardcoded for this one-time script execution)
DB_URL = "postgresql://postgres.luytwntrkdhykiiqnfid:AUSTINjohnson7034232439..@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

def run_patch():
    engine = sqlalchemy.create_engine(DB_URL)
    with engine.begin() as conn:
        print("Fetching Vendors and Ingredients...")
        vendors = conn.execute(text("SELECT id, name, category, tenant_id FROM vendors")).fetchall()
        ingredients = conn.execute(text("SELECT ingredient_name, category, tenant_id FROM ingredients WHERE vendor_id IS NULL")).fetchall()
        
        # Create a category-to-vendor map per tenant
        vendor_map = {}
        for v in vendors:
            key = (v.tenant_id, v.category)
            if key not in vendor_map:
                vendor_map[key] = v.id
        
        updated_count = 0
        for ing in ingredients:
            key = (ing.tenant_id, ing.category)
            vid = vendor_map.get(key)
            
            # Fallback: if no category match, use any vendor for that tenant
            if not vid:
                tenant_vendors = [v.id for v in vendors if v.tenant_id == ing.tenant_id]
                if tenant_vendors:
                    vid = tenant_vendors[0]
            
            if vid:
                conn.execute(
                    text("UPDATE ingredients SET vendor_id = :vid WHERE ingredient_name = :name AND tenant_id = :tid"),
                    {"vid": vid, "name": ing.ingredient_name, "tid": ing.tenant_id}
                )
                updated_count += 1
                
        print(f"Patch complete. Linked {updated_count} ingredients to vendors.")

if __name__ == "__main__":
    run_patch()
