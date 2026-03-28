import pandas as pd

def deduct_all_history():
    from app.services.stock_engine import stock_engine
    grocery, recipes, sales = stock_engine.load_data()

    for idx, row in sales.iterrows():
        item_name = row["item"]
        qty = row["quantity"]
        
        item_recipe = recipes[recipes["menu_item"] == item_name]
        if item_recipe.empty:
            continue
            
        for _, recipe_row in item_recipe.iterrows():
            ingredient = recipe_row["ingredient"]
            qty_per_unit = float(recipe_row["quantity_per_unit"])
            total_needed = qty_per_unit * qty
            
            mask = grocery["ingredient_name"] == ingredient
            if mask.any():
                grocery.loc[mask, "current_stock"] -= total_needed
                
    stock_engine.save_grocery(grocery)
    print("Historical deduction complete!")

if __name__ == "__main__":
    deduct_all_history()
