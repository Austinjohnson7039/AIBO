import pandas as pd
import os
from datetime import datetime

GROCERY_PATH = "data/grocery_stock.csv"
RECIPES_PATH = "data/recipes.csv"
SALES_PATH = "data/sales.csv"

class StockEngine:
    def __init__(self):
        self._ensure_files()
        
    def _ensure_files(self):
        if not os.path.exists(GROCERY_PATH) or not os.path.exists(RECIPES_PATH):
            import subprocess
            subprocess.run(["python", "scripts/create_grocery_data.py"])

    def load_data(self):
        grocery = pd.read_csv(GROCERY_PATH)
        recipes = pd.read_csv(RECIPES_PATH)
        sales = pd.read_csv(SALES_PATH)
        return grocery, recipes, sales
        
    def save_grocery(self, grocery_df):
        cols = ["ingredient_id", "ingredient_name", "category", "unit", "current_stock", "reorder_level", "unit_cost_inr"]
        grocery_df = grocery_df[cols]
        grocery_df.to_csv(GROCERY_PATH, index=False)

    def deduct_sale(self, item_name: str, quantity: int):
        """Deducts ingredients for a single sale event dynamically."""
        grocery, recipes, _ = self.load_data()
        
        # Find recipe for this item
        item_recipe = recipes[recipes["menu_item"] == item_name]
        if item_recipe.empty:
            return  # No recipe mapped, ignore
            
        for _, row in item_recipe.iterrows():
            ingredient = row["ingredient"]
            qty_per_unit = float(row["quantity_per_unit"])
            total_needed = qty_per_unit * quantity
            
            # Deduct from grocery
            mask = grocery["ingredient_name"] == ingredient
            if mask.any():
                grocery.loc[mask, "current_stock"] -= total_needed
                
        self.save_grocery(grocery)

    def restock_item(self, ingredient_name: str, added_amount: float):
        """Restock a specific ingredient."""
        grocery, _, _ = self.load_data()
        mask = grocery["ingredient_name"] == ingredient_name
        if mask.any():
            grocery.loc[mask, "current_stock"] += added_amount
            self.save_grocery(grocery)
            return True
        return False

    def add_grocery_item(self, ingredient_name: str, category: str, unit: str, current_stock: float, reorder_level: float, unit_cost_inr: float):
        """Add a new ingredient to the grocery stock."""
        grocery, _, _ = self.load_data()
        
        # Check if exists
        if ingredient_name in grocery["ingredient_name"].values:
            return False, "Ingredient already exists."
            
        new_id = grocery["ingredient_id"].max() + 1 if not grocery.empty else 1
        new_row = pd.DataFrame([{
            "ingredient_id": new_id,
            "ingredient_name": ingredient_name,
            "category": category,
            "unit": unit,
            "current_stock": current_stock,
            "reorder_level": reorder_level,
            "unit_cost_inr": unit_cost_inr
        }])
        grocery = pd.concat([grocery, new_row], ignore_index=True)
        self.save_grocery(grocery)
        return True, f"Added {ingredient_name}."

    def remove_grocery_item(self, ingredient_name: str):
        """Remove an ingredient from the grocery stock."""
        grocery, _, _ = self.load_data()
        
        if ingredient_name not in grocery["ingredient_name"].values:
            return False, "Ingredient not found."
            
        grocery = grocery[grocery["ingredient_name"] != ingredient_name]
        self.save_grocery(grocery)
        return True, f"Removed {ingredient_name}."

    def edit_grocery_item(self, ingredient_name: str, **kwargs):
        """Edit an existing ingredient's properties in the grocery stock."""
        grocery, _, _ = self.load_data()
        
        mask = grocery["ingredient_name"] == ingredient_name
        if not mask.any():
            return False, f"Ingredient '{ingredient_name}' not found."
            
        valid_cols = ["ingredient_name", "category", "unit", "current_stock", "reorder_level", "unit_cost_inr"]
        updates = []
        for k, v in kwargs.items():
            if k in valid_cols and v is not None:
                grocery.loc[mask, k] = v
                updates.append(f"{k}='{v}'")
                
        if not updates:
            return False, "No valid updates provided."
            
        self.save_grocery(grocery)
        return True, f"Updated {ingredient_name} with: {', '.join(updates)}"

    def get_dashboard_data(self):
        """Returns analytics for UI rendering."""
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
        stock_by_category = grocery.groupby("category")[["ingredient_name", "current_stock", "unit", "reorder_level"]].apply(lambda x: x.to_dict('records')).to_dict()

        # Compute today's consumption
        # We find all sales today, join with recipes, and aggregate
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        sales["date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
        sales["date_only"] = sales["date"].dt.date
        today_sales = sales[sales["date_only"] == now.date()]
        
        consumption = []
        if not today_sales.empty:
            # Join today's sales with recipes
            merged = pd.merge(today_sales, recipes, left_on="item", right_on="menu_item", how="inner")
            merged["total_used"] = merged["quantity"] * merged["quantity_per_unit"]
            # aggregate by ingredient
            agg = merged.groupby(["ingredient", "unit"])["total_used"].sum().reset_index()
            for _, row in agg.iterrows():
                consumption.append({
                    "ingredient": row["ingredient"],
                    "used": row["total_used"],
                    "unit": row["unit"]
                })
                
        # Sales KPIs for the dashboard tab
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
        
        # Top 5 items overall
        top_5_raw = sales.groupby("item")["rev"].sum().sort_values(ascending=False).head(5)
        top_5 = {k: float(v) for k, v in top_5_raw.items()}

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
