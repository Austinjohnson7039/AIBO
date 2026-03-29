import os
import sys

# Set up PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.db.models import Sale, Tenant, Inventory
import random
from datetime import datetime, timedelta

db = SessionLocal()
tenants = db.query(Tenant).all()
for t in tenants:
    # Ensure dummy inventory exists
    invs = db.query(Inventory).filter(Inventory.tenant_id == t.id).all()
    if not invs:
        inv_items = [
            Inventory(tenant_id=t.id, item_name="Fries", category="Snacks", cost_price=40.0, selling_price=100.0),
            Inventory(tenant_id=t.id, item_name="Burger", category="Snacks", cost_price=80.0, selling_price=150.0),
            Inventory(tenant_id=t.id, item_name="Cold Coffee", category="Beverages", cost_price=30.0, selling_price=180.0),
            Inventory(tenant_id=t.id, item_name="Brownie", category="Desserts", cost_price=40.0, selling_price=120.0),
        ]
        db.add_all(inv_items)
        db.commit()

    invs = db.query(Inventory).filter(Inventory.tenant_id == t.id).all()
    
    # Insert 150 dummy sales
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=13)
    sales_list = []
    
    current_date = start_date
    while current_date <= end_date:
        for _ in range(random.randint(8, 15)):
            item = random.choice(invs)
            qty = random.randint(1, 3)
            # Add some noise to price matching
            price = item.selling_price if item.selling_price > 0 else 100.0
            rev = price * qty
            
            # Force peak hours around 6-8 PM for Fries and Burgers
            if item.item_name in ["Fries", "Burger"]:
                hour = random.choice([17, 18, 19, 20]) 
            else:
                hour = random.randint(9, 21)
                
            sales_list.append(Sale(
                tenant_id=t.id, 
                item=item.item_name, 
                quantity=qty, 
                revenue=rev,
                sale_date=current_date.replace(hour=hour, minute=random.randint(0, 59))
            ))
        current_date += timedelta(days=1)
    
    # Don't duplicate indefinitely if script ran
    if db.query(Sale).filter(Sale.tenant_id == t.id).count() < 100:
        db.add_all(sales_list)
        print(f"Added {len(sales_list)} sales to {t.name}")

db.commit()
print("Dummy data fully populated for all accounts!")
