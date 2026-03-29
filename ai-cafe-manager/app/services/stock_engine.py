import pandas as pd
from datetime import datetime
from sqlalchemy import select, update, delete
from app.db.database import SessionLocal
from app.db.models import Ingredient, Recipe, Sale, Inventory

class StockEngine:
    def __init__(self):
        pass

    def load_data(self):
        """
        Loads core stock and sales data as DataFrames for analytical processing.
        Queries Supabase/PostgreSQL instead of local CSVs.
        """
        db = SessionLocal()
        try:
            # Load Ingredients
            ingredients = db.query(Ingredient).all()
            grocery_df = pd.DataFrame([{
                "ingredient_id": i.id,
                "ingredient_name": i.ingredient_name,
                "category": i.category,
                "unit": i.unit,
                "current_stock": i.current_stock,
                "reorder_level": i.reorder_level,
                "unit_cost_inr": i.unit_cost_inr
            } for i in ingredients])

            # Load Recipes
            recipes = db.query(Recipe).all()
            recipes_df = pd.DataFrame([{
                "menu_item": r.menu_item,
                "ingredient": r.ingredient,
                "quantity_per_unit": r.quantity_per_unit,
                "unit": r.unit
            } for r in recipes])

            # Load Sales
            sales = db.query(Sale).all()
            sales_df = pd.DataFrame([{
                "item": s.item,
                "quantity": s.quantity,
                "revenue": s.revenue,
                "sale_date": s.sale_date
            } for s in sales])

            return grocery_df, recipes_df, sales_df
        finally:
            db.close()

    def deduct_sale(self, item_name: str, quantity: int):
        """Deducts ingredients from the cloud database based on recipe mapping."""
        db = SessionLocal()
        try:
            # Find recipe mappings for this menu item
            item_recipes = db.query(Recipe).filter(Recipe.menu_item == item_name).all()
            if not item_recipes:
                return

            for rec in item_recipes:
                total_needed = float(rec.quantity_per_unit) * quantity
                # Update the ingredient stock in DB
                ing = db.query(Ingredient).filter(Ingredient.ingredient_name == rec.ingredient).first()
                if ing:
                    original_stock = ing.current_stock
                    ing.current_stock -= total_needed
                    
                    # Trigger WhatsApp Alert if it crossed the reorder threshold
                    if original_stock > ing.reorder_level and ing.current_stock <= ing.reorder_level:
                        from app.services.whatsapp import send_whatsapp_alert
                        send_whatsapp_alert(f"⚠️ *AIBO Immediate Alert*: Inventory for '{ing.ingredient_name}' has fallen below the reorder threshold. Stock remaining: {ing.current_stock:.1f} {ing.unit}.")

            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def restock_item(self, ingredient_name: str, added_amount: float):
        """Adds stock to a specific ingredient in Supabase."""
        db = SessionLocal()
        try:
            ing = db.query(Ingredient).filter(Ingredient.ingredient_name == ingredient_name).first()
            if ing:
                ing.current_stock += added_amount
                db.commit()
                return True
            return False
        finally:
            db.close()

    def add_grocery_item(self, ingredient_name: str, category: str, unit: str, current_stock: float, reorder_level: float, unit_cost_inr: float):
        """Registers a new ingredient in the cloud database."""
        db = SessionLocal()
        try:
            # Check if exists
            exists = db.query(Ingredient).filter(Ingredient.ingredient_name == ingredient_name).first()
            if exists:
                return False, "Ingredient already exists."
            
            new_ing = Ingredient(
                ingredient_name=ingredient_name,
                category=category,
                unit=unit,
                current_stock=current_stock,
                reorder_level=reorder_level,
                unit_cost_inr=unit_cost_inr
            )
            db.add(new_ing)
            db.commit()
            return True, f"Added {ingredient_name} to Cloud DB."
        finally:
            db.close()

    def remove_grocery_item(self, ingredient_name: str):
        """Deletes an ingredient from Supabase."""
        db = SessionLocal()
        try:
            ing = db.query(Ingredient).filter(Ingredient.ingredient_name == ingredient_name).first()
            if not ing:
                return False, "Ingredient not found."
            
            db.delete(ing)
            db.commit()
            return True, f"Removed {ingredient_name}."
        finally:
            db.close()

    def edit_grocery_item(self, ingredient_name: str, **kwargs):
        """Updates properties of a cloud-hosted ingredient."""
        db = SessionLocal()
        try:
            ing = db.query(Ingredient).filter(Ingredient.ingredient_name == ingredient_name).first()
            if not ing:
                return False, f"Ingredient '{ingredient_name}' not found."
            
            for k, v in kwargs.items():
                if hasattr(ing, k) and v is not None:
                    setattr(ing, k, v)
            
            db.commit()
            return True, f"Updated {ingredient_name} metadata."
        finally:
            db.close()

    def get_dashboard_data(self):
        """Aggregates analytics for the dashboard using cloud data."""
        grocery, recipes, sales = self.load_data()
        
        # Determine alerts
        alerts = []
        for _, row in grocery.iterrows():
            stock = row["current_stock"]
            reorder = row["reorder_level"]
            name = row["ingredient_name"]
            unit = row["unit"]
            
            if stock <= 0:
                alerts.append({"level": "CRITICAL", "item": name, "msg": f"{name} is OUT OF STOCK!"})
            elif stock <= reorder * 0.5:
                alerts.append({"level": "LOW", "item": name, "msg": f"{name} is extremely low ({stock} {unit} left)."})
            elif stock <= reorder:
                alerts.append({"level": "WARNING", "item": name, "msg": f"{name} is below reorder level ({stock} {unit} left)."})

        # Group stock by category for UI
        if not grocery.empty:
            stock_by_category = grocery.groupby("category")[["ingredient_name", "current_stock", "unit", "reorder_level"]].apply(lambda x: x.to_dict('records')).to_dict()
        else:
            stock_by_category = {}

        # Compute today's consumption
        now = datetime.now()
        consumption = []
        if not sales.empty:
            sales["date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
            sales["date_only"] = sales["date"].dt.date
            today_sales = sales[sales["date_only"] == now.date()]
            
            if not today_sales.empty and not recipes.empty:
                merged = pd.merge(today_sales, recipes, left_on="item", right_on="menu_item", how="inner")
                merged["total_used"] = merged["quantity"] * merged["quantity_per_unit"]
                agg = merged.groupby(["ingredient", "unit"])["total_used"].sum().reset_index()
                for _, row in agg.iterrows():
                    consumption.append({
                        "ingredient": row["ingredient"],
                        "used": row["total_used"],
                        "unit": row["unit"]
                    })
                
        # Sales KPIs 
        if not sales.empty:
            sales["rev"] = pd.to_numeric(sales["revenue"], errors="coerce").fillna(0)
            today_rev = float(sales[sales["date_only"] == now.date()]["rev"].sum())
            
            from datetime import timedelta
            week_start = now.date() - timedelta(days=now.date().weekday())
            week_end = week_start + timedelta(days=6)
            week_mask = (sales["date_only"] >= week_start) & (sales["date_only"] <= week_end)
            week_rev = float(sales[week_mask]["rev"].sum())
            
            month_start = now.date().replace(day=1)
            month_mask = (sales["date_only"] >= month_start)
            month_rev = float(sales[month_mask]["rev"].sum())
            
            total_items_sold = int(sales["quantity"].sum())
            top_5_raw = sales.groupby("item")["rev"].sum().sort_values(ascending=False).head(5)
            top_5 = {k: float(v) for k, v in top_5_raw.items()}
        else:
            today_rev = week_rev = month_rev = total_items_sold = 0
            top_5 = {}

        return {
            "alerts": alerts,
            "stock_by_category": stock_by_category,
            "consumption_today": sorted(consumption, key=lambda x: -x["used"]),
            "kpis": {
                "today_rev": today_rev,
                "week_rev": week_rev,
                "month_rev": month_rev,
                "total_items": total_items_sold,
                "top_5": top_5
            },
            "grocery_df": grocery.to_dict('records')
        }

# Global singleton
stock_engine = StockEngine()
