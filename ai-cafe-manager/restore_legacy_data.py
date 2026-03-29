import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base
from app.db.models import Tenant, Sale, Inventory, Ingredient, Recipe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")

def restore_legacy_data(tenant_id: int = 1):
    """Migrates old CSV records into the new Multi-Tenant database schema for a specific tenant."""
    db = SessionLocal()
    try:
        # 1. Restore Sales History
        sales_csv = DATA_DIR / "sales.csv"
        if sales_csv.exists():
            df_sales = pd.read_csv(sales_csv)
            sales_records = []
            for _, row in df_sales.iterrows():
                sales_records.append(Sale(
                    tenant_id=tenant_id,
                    item=row["item"],
                    quantity=int(row["quantity"]),
                    revenue=float(row["revenue"]),
                    sale_date=datetime.fromisoformat(row["sale_date"])
                ))
            db.bulk_save_objects(sales_records)
            logger.info(f"✅ Restored {len(sales_records)} sales records.")

        # 2. Restore Inventory (Menu Items)
        inv_csv = DATA_DIR / "inventory_v2.csv"
        if inv_csv.exists():
            df_inv = pd.read_csv(inv_csv)
            inv_records = []
            for _, row in df_inv.iterrows():
                inv_records.append(Inventory(
                    tenant_id=tenant_id,
                    item_name=row["Item_Name"],
                    category=row.get("Category"),
                    item_type=row.get("Type"),
                    unit=row.get("Unit"),
                    stock=int(row["Stock"]),
                    reorder_level=int(row["Reorder_Level"]),
                    cost_price=float(row.get("Cost_Price", 0.0)),
                    selling_price=float(row.get("Selling_Price", 0.0))
                ))
            db.add_all(inv_records)
            logger.info(f"✅ Restored {len(inv_records)} menu items.")

        # 3. Restore Ingredients (Raw Stock)
        stock_csv = DATA_DIR / "grocery_stock.csv"
        if stock_csv.exists():
            df_stock = pd.read_csv(stock_csv)
            ing_records = []
            for _, row in df_stock.iterrows():
                ing_records.append(Ingredient(
                    tenant_id=tenant_id,
                    ingredient_name=row["ingredient_name"],
                    category=row.get("category", "General"),
                    unit=row.get("unit", "units"),
                    current_stock=float(row["current_stock"]),
                    reorder_level=float(row["reorder_level"]),
                    unit_cost_inr=float(row.get("unit_cost_inr", 0.0))
                ))
            db.add_all(ing_records)
            logger.info(f"✅ Restored {len(ing_records)} ingredients.")

        # 4. Restore Recipes
        recipes_csv = DATA_DIR / "recipes.csv"
        if recipes_csv.exists():
            df_recipes = pd.read_csv(recipes_csv)
            rec_records = []
            for _, row in df_recipes.iterrows():
                rec_records.append(Recipe(
                    tenant_id=tenant_id,
                    menu_item=row["menu_item"],
                    ingredient=row["ingredient"],
                    quantity_per_unit=float(row["quantity_per_unit"]),
                    unit=row.get("unit")
                ))
            db.add_all(rec_records)
            logger.info(f"✅ Restored {len(rec_records)} recipes.")

        db.commit()
        logger.info("🎉 Migration complete. Data restored for Tenant ID 1.")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    restore_legacy_data(1)
