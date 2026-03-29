import pandas as pd
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, SessionLocal, Base
from app.db.models import Sale, Inventory, Ingredient, Recipe

def migrate():
    print("🚀 Starting Supabase Migration...")

    # 1. Create Tables in Supabase
    print("--- Creating Tables ---")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Migrate Menu Inventory from CSV
        print("--- Migrating Menu Inventory ---")
        inv_path = "data/inventory_v2.csv"
        if os.path.exists(inv_path):
            df_inv = pd.read_csv(inv_path)
            for _, row in df_inv.iterrows():
                item = Inventory(
                    id=int(row["Item_ID"]),
                    item_name=str(row["Item_Name"]),
                    category=str(row.get("Category", "Uncategorized")),
                    item_type=str(row.get("Type", "General")),
                    unit=str(row.get("Unit", "pcs")),
                    supplier=str(row.get("Supplier", "Local")),
                    stock=int(row.get("Stock", 0)),
                    reorder_level=int(row.get("Reorder_Level", 10)),
                    cost_price=float(row.get("Cost_Price", 0.0)),
                    selling_price=float(row.get("Selling_Price", 0.0))
                )
                db.merge(item) # merge handles existing IDs
            db.commit()
            print(f"✅ Migrated {len(df_inv)} menu items.")

        # 3. Migrate Sales from CSV
        print("--- Migrating Sales History ---")
        sales_path = "data/sales.csv"
        if os.path.exists(sales_path):
            df_sales = pd.read_csv(sales_path)
            # Clear existing sales to avoid duplicates on fresh migration
            db.query(Sale).delete()
            for _, row in df_sales.iterrows():
                sale = Sale(
                    item=str(row["item"]),
                    quantity=int(row["quantity"]),
                    revenue=float(row["revenue"]),
                    sale_date=pd.to_datetime(row["sale_date"])
                )
                db.add(sale)
            db.commit()
            print(f"✅ Migrated {len(df_sales)} sales records.")

        # 4. Migrate Ingredients (Grocery)
        print("--- Migrating Grocery Ingredients ---")
        groc_path = "data/grocery_stock.csv"
        if os.path.exists(groc_path):
            df_groc = pd.read_csv(groc_path)
            for _, row in df_groc.iterrows():
                ing = Ingredient(
                    id=int(row["ingredient_id"]),
                    ingredient_name=str(row["ingredient_name"]),
                    category=str(row["category"]),
                    unit=str(row["unit"]),
                    current_stock=float(row["current_stock"]),
                    reorder_level=float(row["reorder_level"]),
                    unit_cost_inr=float(row["unit_cost_inr"])
                )
                db.merge(ing)
            db.commit()
            print(f"✅ Migrated {len(df_groc)} ingredients.")

        # 5. Migrate Recipes
        print("--- Migrating Recipes ---")
        rec_path = "data/recipes.csv"
        if os.path.exists(rec_path):
            df_rec = pd.read_csv(rec_path)
            # Clear existing recipes
            db.query(Recipe).delete()
            for _, row in df_rec.iterrows():
                recipe = Recipe(
                    menu_item=str(row["menu_item"]),
                    ingredient=str(row["ingredient"]),
                    quantity_per_unit=float(row["quantity_per_unit"]),
                    unit=str(row.get("unit", ""))
                )
                db.add(recipe)
            db.commit()
            print(f"✅ Migrated {len(df_rec)} recipe mappings.")

        print("\n🎉 MIGRATION COMPLETE!")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
