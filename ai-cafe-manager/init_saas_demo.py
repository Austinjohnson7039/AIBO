from app.db.database import SessionLocal, engine, Base
from app.db.models import Tenant, Inventory, Ingredient, Recipe, Vendor
from app.api.auth import get_password_hash
import os

def init_saas_demo():
    print("🚀 Initializing AIBO SaaS Multi-Tenant Demo...")
    
    # 1. Wipe & Recreate Schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Create the First Tenant (Cafe)
        demo_tenant = Tenant(
            name="The Caffeine Hub (Indiranagar)",
            email="admin@hub.com",
            password_hash=get_password_hash("cafe123"),
            location="Bengaluru"
        )
        db.add(demo_tenant)
        db.commit()
        db.refresh(demo_tenant)
        tid = demo_tenant.id
        print(f"✅ Created Tenant: {demo_tenant.name} (ID: {tid})")

        # 3. Add Inventory
        items = [
            Inventory(tenant_id=tid, item_name="Hot Cappuccino", category="Hot Coffee", stock=50, selling_price=180, cost_price=45),
            Inventory(tenant_id=tid, item_name="Iced Cold Brew", category="Cold Coffee", stock=30, selling_price=220, cost_price=60),
            Inventory(tenant_id=tid, item_name="Chocolate Frappe", category="Blended", stock=100, selling_price=250, cost_price=85),
            Inventory(tenant_id=tid, item_name="Classic Latte", category="Hot Coffee", stock=40, selling_price=190, cost_price=50),
        ]
        db.add_all(items)
        
        # 4. Add Ingredients (Raw Stock)
        ings = [
            Ingredient(tenant_id=tid, ingredient_name="Whole Milk", category="Dairy", unit="L", current_stock=5.0, reorder_level=15.0),
            Ingredient(tenant_id=tid, ingredient_name="Coffee Beans (Arabica)", category="Beans", unit="kg", current_stock=2.0, reorder_level=5.0),
            Ingredient(tenant_id=tid, ingredient_name="Chocolate Syrup", category="Syrups", unit="ml", current_stock=2000, reorder_level=1000),
            Ingredient(tenant_id=tid, ingredient_name="Paper Cups (Regular)", category="Packing", unit="units", current_stock=400, reorder_level=200),
        ]
        db.add_all(ings)
        
        # 5. Add a Vendor
        v = Vendor(tenant_id=tid, name="Nandini Dairy", contact_name="Suresh", whatsapp_number="919999999999", category="Dairy")
        db.add(v)
        
        db.commit()
        print("🎉 Demo Environment Ready! Login with admin@hub.com / cafe123")
        
    finally:
        db.close()

if __name__ == "__main__":
    init_saas_demo()
