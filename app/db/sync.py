"""
sync.py
───────
Utility to synchronize the SQLite database state back to the source CSV files.
Allows the "agentic" modifications to persist in the human-readable data/ folder.
"""

import logging
from pathlib import Path
import pandas as pd
from app.db.database import SessionLocal
from app.db.models import Sale, Inventory

logger = logging.getLogger(__name__)

# Resolve the data/ directory relative to the project root
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

def sync_to_csv() -> bool:
    """Export current SQLite tables to sales.csv and inventory.csv."""
    db = SessionLocal()
    try:
        # 1. Sync Sales
        sales = db.query(Sale).all()
        if sales:
            sales_df = pd.DataFrame([
                {
                    "item": s.item, 
                    "quantity": s.quantity, 
                    "revenue": s.revenue, 
                    "sale_date": s.sale_date.strftime("%Y-%m-%d %H:%M:%S") if s.sale_date else ""
                } for s in sales
            ])
            sales_df.to_csv(_DATA_DIR / "sales.csv", index=False)
            logger.info("Synced %d sales records to sales.csv", len(sales))

        # 2. Sync Inventory
        inventory = db.query(Inventory).all()
        if inventory:
            inv_df = pd.DataFrame([
                {
                    "Item_ID": i.id,
                    "Item_Name": i.item_name,
                    "Category": i.category,
                    "Type": i.item_type,
                    "Stock": i.stock,
                    "Reorder_Level": i.reorder_level,
                    "Unit": i.unit,
                    "Cost_Price": i.cost_price,
                    "Selling_Price": i.selling_price,
                    "Supplier": i.supplier
                } for i in inventory
            ])
            inv_df.to_csv(_DATA_DIR / "inventory_v2.csv", index=False)
            logger.info("Synced %d inventory items to inventory_v2.csv", len(inventory))
            
        return True
    except Exception as e:
        logger.error("Failed to sync database to CSV: %s", e)
        return False
    finally:
        db.close()
