import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from app.db.models import Ingredient, Recipe, Sale, Inventory, Tenant

class StockEngine:
    def __init__(self):
        pass

    def load_data(self, db: Session, tenant_id: int):
        """Loads tenant-specific stock and sales data as DataFrames."""
        # Load Ingredients
        ingredients = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id).all()
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
        recipes = db.query(Recipe).filter(Recipe.tenant_id == tenant_id).all()
        recipes_df = pd.DataFrame([{
            "menu_item": r.menu_item,
            "ingredient": r.ingredient,
            "quantity_per_unit": r.quantity_per_unit,
            "unit": r.unit
        } for r in recipes])

        # Load Sales
        sales = db.query(Sale).filter(Sale.tenant_id == tenant_id).all()
        sales_df = pd.DataFrame([{
            "item": s.item,
            "quantity": s.quantity,
            "revenue": s.revenue,
            "sale_date": s.sale_date
        } for s in sales])

        # Load Inventory
        inventories = db.query(Inventory).filter(Inventory.tenant_id == tenant_id).all()
        inv_df = pd.DataFrame([{
            "item_name": i.item_name,
            "category": i.category,
            "cost_price": i.cost_price
        } for i in inventories])

        return grocery_df, recipes_df, sales_df, inv_df

    def record_sale_and_deduct(self, db: Session, tenant_id: int, item_name: str, quantity: int, revenue: float):
        """Records a sale and deducts ingredients for a specific tenant."""
        try:
            # 1. Record Sale
            new_sale = Sale(tenant_id=tenant_id, item=item_name, quantity=quantity, revenue=revenue)
            db.add(new_sale)
            
            # 2. Deduct Ingredients
            item_recipes = db.query(Recipe).filter(Recipe.tenant_id == tenant_id, Recipe.menu_item == item_name).all()
            for rec in item_recipes:
                total_needed = float(rec.quantity_per_unit) * quantity
                ing = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id, Ingredient.ingredient_name == rec.ingredient).first()
                if ing:
                    original_stock = ing.current_stock
                    ing.current_stock -= total_needed
                    
                    # Alert if crossed threshold
                    if original_stock > ing.reorder_level and ing.current_stock <= ing.reorder_level:
                        from app.services.whatsapp import send_whatsapp_alert
                        send_whatsapp_alert(f"⚠️ *AIBO ({tenant_id})*: '{ing.ingredient_name}' low stock: {ing.current_stock:.1f} {ing.unit}.")

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Deduction error: {e}")

    def restock_item(self, db: Session, tenant_id: int, ingredient_name: str, added_amount: float):
        """Adds stock for a tenant's ingredient."""
        ing = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id, Ingredient.ingredient_name == ingredient_name).first()
        if ing:
            ing.current_stock += added_amount
            db.commit()
            return True
        return False

    def add_grocery_item(self, db: Session, tenant_id: int, req_data):
        """Registers a new ingredient for a tenant."""
        exists = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id, Ingredient.ingredient_name == req_data.ingredient_name).first()
        if exists:
            return False, "Ingredient already exists."
        
        new_ing = Ingredient(tenant_id=tenant_id, **req_data.dict())
        db.add(new_ing)
        db.commit()
        return True, f"Registered {req_data.ingredient_name}."

    def remove_grocery_item(self, db: Session, tenant_id: int, ingredient_name: str):
        """Deletes a tenant's ingredient."""
        ing = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id, Ingredient.ingredient_name == ingredient_name).first()
        if not ing:
            return False, "Not found."
        db.delete(ing)
        db.commit()
        return True, f"Removed {ingredient_name}."

    def get_dashboard_data(self, db: Session, tenant_id: int):
        """Aggregates analytics scoped to a single tenant."""
        grocery, recipes, sales, inv_df = self.load_data(db, tenant_id)
        
        alerts = []
        if not grocery.empty:
            for _, row in grocery.iterrows():
                stock, reorder, name, unit = row["current_stock"], row["reorder_level"], row["ingredient_name"], row["unit"]
                if stock <= 0:
                    alerts.append({"level": "CRITICAL", "item": name, "msg": f"{name} is OUT OF STOCK!"})
                elif stock <= reorder:
                    alerts.append({"level": "WARNING", "item": name, "msg": f"{name} low ({stock} {unit})."})

            stock_by_category = grocery.groupby("category")[["ingredient_name", "current_stock", "unit", "reorder_level"]].apply(lambda x: x.to_dict('records')).to_dict()
        else:
            stock_by_category = {}

        # Sales KPIs
        now = datetime.now()
        today_rev = 0
        total_rev = 0
        total_items_sold = 0
        top_5 = {}
        consumption = []

        if not sales.empty:
            sales["date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
            sales["date_only"] = sales["date"].dt.date
            today_sales = sales[sales["date_only"] == now.date()]
            
            today_rev = float(today_sales["revenue"].sum())
            total_rev = float(sales["revenue"].sum())
            total_items_sold = int(sales["quantity"].sum())
            
            # Top 5 items by revenue
            top_5 = sales.groupby("item")["revenue"].sum().sort_values(ascending=False).head(5).to_dict()
            
            # Consumption today
            if not today_sales.empty and not recipes.empty:
                merged = pd.merge(today_sales, recipes, left_on="item", right_on="menu_item", how="inner")
                merged["total_used"] = merged["quantity"] * merged["quantity_per_unit"]
                agg = merged.groupby(["ingredient", "unit"])["total_used"].sum().reset_index()
                consumption = agg.to_dict('records')

        # ── Advanced Reports Generation ──
        advanced_reports = {
            "daily_sales": [],
            "category_performance": [],
            "peak_hours": [],
            "gross_margin_pct": 0.0,
            "ai_insight": "Not enough data for insights."
        }

        if not sales.empty:
            # 1. Daily Sales
            recent_sales = sales[sales["date_only"] >= (now.date() - timedelta(days=14))]
            if not recent_sales.empty:
                daily_grp = recent_sales.groupby("date_only")["revenue"].sum().reset_index()
                daily_grp["date_str"] = daily_grp["date_only"].astype(str)
                dr = daily_grp[["date_str", "revenue"]].rename(columns={"date_str": "date"}).to_dict('records')
                advanced_reports["daily_sales"] = [{"date": r["date"], "revenue": float(r["revenue"])} for r in dr]
            
            # 2. Category Performance
            category_sales = sales.copy()
            if not inv_df.empty:
                category_sales = pd.merge(category_sales, inv_df, left_on="item", right_on="item_name", how="left")
                category_sales["category"] = category_sales["category"].fillna("Uncategorized")
                category_sales["cost_price"] = category_sales["cost_price"].fillna(0.0)
            else:
                category_sales["category"] = "Uncategorized"
                category_sales["cost_price"] = 0.0
            
            cat_perf = category_sales.groupby("category")["revenue"].sum().reset_index().to_dict('records')
            advanced_reports["category_performance"] = [{"category": str(r["category"]), "revenue": float(r["revenue"])} for r in cat_perf]
            
            # 3. Peak Hours
            sales["hour"] = sales["date"].dt.hour
            hour_grp = sales.groupby("hour")["revenue"].sum().reset_index()
            hour_grp["hour_str"] = hour_grp["hour"].apply(lambda h: f"{int(h):02d}:00")
            hr = hour_grp[["hour_str", "revenue"]].rename(columns={"hour_str": "hour"}).to_dict('records')
            advanced_reports["peak_hours"] = [{"hour": r["hour"], "revenue": float(r["revenue"])} for r in hr]
            
            # 4. Profit Margin (Total Rev - COGS)
            total_cost = 0.0
            if "cost_price" in category_sales.columns:
                category_sales["total_cost"] = category_sales["quantity"] * category_sales["cost_price"]
                tc = category_sales["total_cost"].sum()
                if not pd.isna(tc):
                    total_cost = tc
            
            if total_cost == 0 and not recipes.empty and not grocery.empty:
                sales_recipe = pd.merge(sales, recipes, left_on="item", right_on="menu_item", how="inner")
                sales_recipe_gro = pd.merge(sales_recipe, grocery, left_on="ingredient", right_on="ingredient_name", how="inner")
                sales_recipe_gro["cogs"] = sales_recipe_gro["quantity"] * sales_recipe_gro["quantity_per_unit"] * sales_recipe_gro["unit_cost_inr"]
                tc2 = sales_recipe_gro["cogs"].sum()
                if not pd.isna(tc2):
                    total_cost = tc2

            gross_profit = float(total_rev) - float(total_cost)
            margin_pct = (gross_profit / float(total_rev) * 100) if float(total_rev) > 0 else 0.0
            advanced_reports["gross_margin_pct"] = round(float(margin_pct), 1)

            # 5. AI Peak Hour Insight
            item_hour_grp = sales.groupby(["item", "hour"])["quantity"].sum().reset_index()
            if not item_hour_grp.empty:
                best_row = item_hour_grp.loc[item_hour_grp["quantity"].idxmax()]
                best_item = best_row["item"]
                best_hour = int(best_row["hour"])
                end_hour = best_hour + 1
                
                def fmt_time(h):
                    am_pm = "AM" if h < 12 else "PM"
                    hr = h if h <= 12 else h - 12
                    hr = 12 if hr == 0 else hr
                    return f"{hr} {am_pm}"
                
                advanced_reports["ai_insight"] = f"🔥 AI Insight: {str(best_item)} sells best between {fmt_time(best_hour)} - {fmt_time(end_hour)}"

        # Inventory list for the grocery tab
        inventory_list = []
        if not grocery.empty:
            for _, row in grocery.iterrows():
                inventory_list.append({
                    "ingredient_name": row["ingredient_name"],
                    "category": row["category"],
                    "current_stock": row["current_stock"],
                    "reorder_level": row["reorder_level"],
                    "unit": row["unit"],
                    "unit_cost_inr": row["unit_cost_inr"]
                })

        return {
            "alerts": alerts,
            "stock_by_category": stock_by_category,
            "inventory": inventory_list,
            "consumption_today": consumption,
            "advanced_reports": advanced_reports,
            "kpis": {
                "today_rev": today_rev,
                "total_rev": total_rev,
                "total_items": total_items_sold,
                "top_5": top_5
            }
        }

stock_engine = StockEngine()
