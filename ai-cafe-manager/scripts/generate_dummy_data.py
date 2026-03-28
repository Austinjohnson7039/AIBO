import random
from datetime import datetime, timedelta
import pandas as pd
from app.db.database import SessionLocal
from app.db.models import Sale, Inventory
from app.db.sync import sync_to_csv

def generate_dummy_sales():
    db = SessionLocal()
    try:
        # 1. Fetch current inventory items to sell
        inventory = db.query(Inventory).all()
        if not inventory:
            print("No inventory found. Cannot generate sales.")
            return

        # 2. Define some basic prices if they are 0.0 (just for dummy sales)
        # Category based pricing mapping
        category_prices = {
            "Combo": (15.0, 25.0),
            "Snacks": (5.0, 10.0),
            "Burger": (8.0, 18.0),
            "Sandwich": (6.0, 12.0),
            "Drinks": (3.0, 10.0),
            "Wrap": (7.0, 14.0)
        }

        # 3. Generate 30 days of data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Clear existing sales if any? 
        # (Optional, but I'll append to avoid data loss if user had something)
        # db.query(Sale).delete() 

        all_new_sales = []
        
        current_date = start_date
        while current_date <= end_date:
            # Generate 5-15 sales per day
            num_sales = random.randint(5, 15)
            for _ in range(num_sales):
                item = random.choice(inventory)
                qty = random.randint(1, 4)
                
                # Use item's price if set, else use category default
                price_range = category_prices.get(item.category, (5.0, 15.0))
                price = item.selling_price if item.selling_price > 0 else random.uniform(*price_range)
                
                revenue = round(price * qty, 2)
                
                new_sale = Sale(
                    item=item.item_name,
                    quantity=qty,
                    revenue=revenue,
                    sale_date=current_date.replace(hour=random.randint(9, 21), minute=random.randint(0, 59))
                )
                db.add(new_sale)
                all_new_sales.append(new_sale)
            
            current_date += timedelta(days=1)
        
        db.commit()
        print(f"Generated {len(all_new_sales)} dummy sales records in database.")
        
        # 4. Sync to CSV
        if sync_to_csv():
            print("Successfully synced sales to data/sales.csv")
        else:
            print("Failed to sync to CSV.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_dummy_sales()
