import pandas as pd
import os

def create_grocery_data():
    inventory_path = "data/inventory_v2.csv"
    if not os.path.exists(inventory_path):
        print("inventory_v2.csv missing!")
        return

    # Load inventory
    inv_df = pd.read_csv(inventory_path)
    
    # 1. Define Grocery Ingredients
    ingredients = [
        {"ingredient_name": "Burger Bun", "category": "Bakery", "unit": "pcs", "current_stock": 200, "reorder_level": 50, "unit_cost_inr": 15},
        {"ingredient_name": "Chicken Breast", "category": "Meat", "unit": "g", "current_stock": 10000, "reorder_level": 3000, "unit_cost_inr": 0.25},  # 250 rs/kg
        {"ingredient_name": "Minced Beef", "category": "Meat", "unit": "g", "current_stock": 5000, "reorder_level": 2000, "unit_cost_inr": 0.35},
        {"ingredient_name": "Sandwich Bread", "category": "Bakery", "unit": "slice", "current_stock": 100, "reorder_level": 20, "unit_cost_inr": 5},
        {"ingredient_name": "Potato", "category": "Vegetable", "unit": "g", "current_stock": 15000, "reorder_level": 5000, "unit_cost_inr": 0.04},
        {"ingredient_name": "Onion", "category": "Vegetable", "unit": "g", "current_stock": 5000, "reorder_level": 1500, "unit_cost_inr": 0.05},
        {"ingredient_name": "Lettuce (Iceberg)", "category": "Vegetable", "unit": "g", "current_stock": 2000, "reorder_level": 500, "unit_cost_inr": 0.1},
        {"ingredient_name": "Tomato", "category": "Vegetable", "unit": "g", "current_stock": 3000, "reorder_level": 1000, "unit_cost_inr": 0.06},
        {"ingredient_name": "Cheese Slice", "category": "Dairy", "unit": "pcs", "current_stock": 150, "reorder_level": 30, "unit_cost_inr": 12},
        {"ingredient_name": "Paneer", "category": "Dairy", "unit": "g", "current_stock": 2000, "reorder_level": 500, "unit_cost_inr": 0.3},
        {"ingredient_name": "Zinger Sauce", "category": "Sauce", "unit": "ml", "current_stock": 2000, "reorder_level": 500, "unit_cost_inr": 0.2},
        {"ingredient_name": "Mayo", "category": "Sauce", "unit": "ml", "current_stock": 3000, "reorder_level": 1000, "unit_cost_inr": 0.15},
        {"ingredient_name": "Lime", "category": "Fruit", "unit": "pcs", "current_stock": 100, "reorder_level": 20, "unit_cost_inr": 3},
        {"ingredient_name": "Ginger", "category": "Vegetable", "unit": "g", "current_stock": 500, "reorder_level": 100, "unit_cost_inr": 0.12},
        {"ingredient_name": "Apple", "category": "Fruit", "unit": "pcs", "current_stock": 50, "reorder_level": 10, "unit_cost_inr": 20},
        {"ingredient_name": "Orange", "category": "Fruit", "unit": "pcs", "current_stock": 60, "reorder_level": 15, "unit_cost_inr": 10},
        {"ingredient_name": "Grape", "category": "Fruit", "unit": "g", "current_stock": 2000, "reorder_level": 500, "unit_cost_inr": 0.1},
        {"ingredient_name": "Watermelon", "category": "Fruit", "unit": "g", "current_stock": 5000, "reorder_level": 1000, "unit_cost_inr": 0.05},
        {"ingredient_name": "Pineapple", "category": "Fruit", "unit": "g", "current_stock": 3000, "reorder_level": 1000, "unit_cost_inr": 0.08},
        {"ingredient_name": "Banana", "category": "Fruit", "unit": "pcs", "current_stock": 80, "reorder_level": 20, "unit_cost_inr": 5},
        {"ingredient_name": "Milk", "category": "Dairy", "unit": "ml", "current_stock": 10000, "reorder_level": 2000, "unit_cost_inr": 0.06},
        {"ingredient_name": "Ice Cream", "category": "Dairy", "unit": "ml", "current_stock": 5000, "reorder_level": 1000, "unit_cost_inr": 0.25},
        {"ingredient_name": "Oreo", "category": "Grocery", "unit": "pcs", "current_stock": 100, "reorder_level": 20, "unit_cost_inr": 5},
        {"ingredient_name": "KitKat", "category": "Grocery", "unit": "pcs", "current_stock": 50, "reorder_level": 10, "unit_cost_inr": 20},
        {"ingredient_name": "Snickers", "category": "Grocery", "unit": "pcs", "current_stock": 50, "reorder_level": 10, "unit_cost_inr": 40},
        {"ingredient_name": "Avocado", "category": "Fruit", "unit": "pcs", "current_stock": 20, "reorder_level": 5, "unit_cost_inr": 60},
        {"ingredient_name": "Blueberry", "category": "Fruit", "unit": "g", "current_stock": 1000, "reorder_level": 200, "unit_cost_inr": 1.5},
        {"ingredient_name": "Frying Oil", "category": "Grocery", "unit": "ml", "current_stock": 15000, "reorder_level": 5000, "unit_cost_inr": 0.15},
        {"ingredient_name": "Tortilla Wrap", "category": "Bakery", "unit": "pcs", "current_stock": 100, "reorder_level": 20, "unit_cost_inr": 10},
    ]
    
    for i, ing in enumerate(ingredients, start=1):
        ing["ingredient_id"] = i

    grocery_df = pd.DataFrame(ingredients)
    cols = ["ingredient_id", "ingredient_name", "category", "unit", "current_stock", "reorder_level", "unit_cost_inr"]
    grocery_df = grocery_df[cols]
    grocery_df.to_csv("data/grocery_stock.csv", index=False)
    print("Created grocery_stock.csv")

    # 2. Create Recipes Mapping
    recipes = []
    
    for idx, row in inv_df.iterrows():
        item = row["Item_Name"]
        menu_type = str(row.get("Type", ""))
        
        # Base ingredients by Category
        if "Burger" in item:
            recipes.append({"menu_item": item, "ingredient": "Burger Bun", "quantity_per_unit": 1, "unit": "pcs"})
            recipes.append({"menu_item": item, "ingredient": "Lettuce (Iceberg)", "quantity_per_unit": 20, "unit": "g"})
            recipes.append({"menu_item": item, "ingredient": "Onion", "quantity_per_unit": 10, "unit": "g"})
            recipes.append({"menu_item": item, "ingredient": "Tomato", "quantity_per_unit": 15, "unit": "g"})
            recipes.append({"menu_item": item, "ingredient": "Mayo", "quantity_per_unit": 15, "unit": "ml"})
            
            if "Chicken" in item or "Zinger" in item:
                recipes.append({"menu_item": item, "ingredient": "Chicken Breast", "quantity_per_unit": 120, "unit": "g"})
                recipes.append({"menu_item": item, "ingredient": "Zinger Sauce", "quantity_per_unit": 20, "unit": "ml"})
            elif "Beef" in item:
                recipes.append({"menu_item": item, "ingredient": "Minced Beef", "quantity_per_unit": 120, "unit": "g"})
            elif "Veg" in item:
                recipes.append({"menu_item": item, "ingredient": "Potato", "quantity_per_unit": 80, "unit": "g"})
                
            if "Cheese" in item:
                recipes.append({"menu_item": item, "ingredient": "Cheese Slice", "quantity_per_unit": 1, "unit": "pcs"})
            if "Double" in item or "Jumbo" in item or "Mega" in item:
                # Double meat/patty
                if "Chicken" in item or "Zinger" in item:
                    recipes.append({"menu_item": item, "ingredient": "Chicken Breast", "quantity_per_unit": 80, "unit": "g"})
                elif "Beef" in item:
                    recipes.append({"menu_item": item, "ingredient": "Minced Beef", "quantity_per_unit": 80, "unit": "g"})
                elif "Veg" in item:
                    recipes.append({"menu_item": item, "ingredient": "Potato", "quantity_per_unit": 50, "unit": "g"})
            if "Triple X" in item:
                if "Chicken" in item:
                    recipes.append({"menu_item": item, "ingredient": "Chicken Breast", "quantity_per_unit": 150, "unit": "g"})
                elif "Beef" in item:
                    recipes.append({"menu_item": item, "ingredient": "Minced Beef", "quantity_per_unit": 150, "unit": "g"})
                elif "Veg" in item:
                    recipes.append({"menu_item": item, "ingredient": "Potato", "quantity_per_unit": 100, "unit": "g"})
            if "Lime" in item:
                recipes.append({"menu_item": item, "ingredient": "Lime", "quantity_per_unit": 0.5, "unit": "pcs"})
                
        elif "Wrap" in item:
            recipes.append({"menu_item": item, "ingredient": "Tortilla Wrap", "quantity_per_unit": 1, "unit": "pcs"})
            recipes.append({"menu_item": item, "ingredient": "Lettuce (Iceberg)", "quantity_per_unit": 30, "unit": "g"})
            recipes.append({"menu_item": item, "ingredient": "Onion", "quantity_per_unit": 15, "unit": "g"})
            recipes.append({"menu_item": item, "ingredient": "Mayo", "quantity_per_unit": 20, "unit": "ml"})
            
            if "Chicken" in item or "Zinger" in item:
                recipes.append({"menu_item": item, "ingredient": "Chicken Breast", "quantity_per_unit": 100, "unit": "g"})
                recipes.append({"menu_item": item, "ingredient": "Zinger Sauce", "quantity_per_unit": 15, "unit": "ml"})
            elif "Paneer" in item:
                recipes.append({"menu_item": item, "ingredient": "Paneer", "quantity_per_unit": 80, "unit": "g"})
            elif "Vegetable" in item:
                recipes.append({"menu_item": item, "ingredient": "Potato", "quantity_per_unit": 60, "unit": "g"})
                recipes.append({"menu_item": item, "ingredient": "Tomato", "quantity_per_unit": 20, "unit": "g"})
                
            if "Cheese" in item:
                recipes.append({"menu_item": item, "ingredient": "Cheese Slice", "quantity_per_unit": 1, "unit": "pcs"})

        elif "Sandwich" in item:
            recipes.append({"menu_item": item, "ingredient": "Sandwich Bread", "quantity_per_unit": 2, "unit": "slice"})
            recipes.append({"menu_item": item, "ingredient": "Mayo", "quantity_per_unit": 15, "unit": "ml"})
            recipes.append({"menu_item": item, "ingredient": "Tomato", "quantity_per_unit": 15, "unit": "g"})
            recipes.append({"menu_item": item, "ingredient": "Lettuce (Iceberg)", "quantity_per_unit": 10, "unit": "g"})
            
            if "Chicken" in item or "Zinger" in item:
                recipes.append({"menu_item": item, "ingredient": "Chicken Breast", "quantity_per_unit": 80, "unit": "g"})
            elif "Beef" in item:
                recipes.append({"menu_item": item, "ingredient": "Minced Beef", "quantity_per_unit": 80, "unit": "g"})
            elif "Veg" in item:
                recipes.append({"menu_item": item, "ingredient": "Potato", "quantity_per_unit": 50, "unit": "g"})

            if "Cheese" in item:
                recipes.append({"menu_item": item, "ingredient": "Cheese Slice", "quantity_per_unit": 1, "unit": "pcs"})
                
        elif "Fries" in item:
            recipes.append({"menu_item": item, "ingredient": "Potato", "quantity_per_unit": 150, "unit": "g"})
            recipes.append({"menu_item": item, "ingredient": "Frying Oil", "quantity_per_unit": 20, "unit": "ml"})
            
            if "Loaded" in item:
                recipes.append({"menu_item": item, "ingredient": "Mayo", "quantity_per_unit": 30, "unit": "ml"})
                recipes.append({"menu_item": item, "ingredient": "Cheese Slice", "quantity_per_unit": 1, "unit": "pcs"})
                if "Chicken" in item or "Zinger" in item:
                    recipes.append({"menu_item": item, "ingredient": "Chicken Breast", "quantity_per_unit": 60, "unit": "g"})
                elif "Beef" in item:
                    recipes.append({"menu_item": item, "ingredient": "Minced Beef", "quantity_per_unit": 60, "unit": "g"})

        elif "Nuggets" in item or "Strips" in item:
            recipes.append({"menu_item": item, "ingredient": "Frying Oil", "quantity_per_unit": 30, "unit": "ml"})
            if "Chicken" in item:
                recipes.append({"menu_item": item, "ingredient": "Chicken Breast", "quantity_per_unit": 120, "unit": "g"})
            elif "Veg" in item:
                recipes.append({"menu_item": item, "ingredient": "Potato", "quantity_per_unit": 100, "unit": "g"})
                
        elif "Shake" in item or "Milkshake" in item:
            recipes.append({"menu_item": item, "ingredient": "Milk", "quantity_per_unit": 250, "unit": "ml"})
            recipes.append({"menu_item": item, "ingredient": "Ice Cream", "quantity_per_unit": 100, "unit": "ml"})
            if "Oreo" in item:
                recipes.append({"menu_item": item, "ingredient": "Oreo", "quantity_per_unit": 4, "unit": "pcs"})
            elif "KitKat" in item:
                recipes.append({"menu_item": item, "ingredient": "KitKat", "quantity_per_unit": 2, "unit": "pcs"})
            elif "Snickers" in item:
                recipes.append({"menu_item": item, "ingredient": "Snickers", "quantity_per_unit": 2, "unit": "pcs"})
            elif "Avocado" in item:
                recipes.append({"menu_item": item, "ingredient": "Avocado", "quantity_per_unit": 0.5, "unit": "pcs"})
            elif "Blueberry" in item:
                recipes.append({"menu_item": item, "ingredient": "Blueberry", "quantity_per_unit": 40, "unit": "g"})
            elif "banana" in item.lower():
                recipes.append({"menu_item": item, "ingredient": "Banana", "quantity_per_unit": 1.5, "unit": "pcs"})
                
        elif "Juice" in item or "Lime" in item:
            if "Lime" in item and "Fresh" in item:
                recipes.append({"menu_item": item, "ingredient": "Lime", "quantity_per_unit": 2, "unit": "pcs"})
            elif "Ginger" in item:
                recipes.append({"menu_item": item, "ingredient": "Lime", "quantity_per_unit": 1, "unit": "pcs"})
                recipes.append({"menu_item": item, "ingredient": "Ginger", "quantity_per_unit": 10, "unit": "g"})
            elif "Apple" in item:
                recipes.append({"menu_item": item, "ingredient": "Apple", "quantity_per_unit": 2, "unit": "pcs"})
            elif "Orange" in item:
                recipes.append({"menu_item": item, "ingredient": "Orange", "quantity_per_unit": 3, "unit": "pcs"})
            elif "Grape" in item:
                recipes.append({"menu_item": item, "ingredient": "Grape", "quantity_per_unit": 250, "unit": "g"})
            elif "Watermelon" in item:
                recipes.append({"menu_item": item, "ingredient": "Watermelon", "quantity_per_unit": 300, "unit": "g"})
            elif "Pineapple" in item:
                recipes.append({"menu_item": item, "ingredient": "Pineapple", "quantity_per_unit": 250, "unit": "g"})

    recipes_df = pd.DataFrame(recipes)
    recipes_df.to_csv("data/recipes.csv", index=False)
    print("Created recipes.csv")

if __name__ == "__main__":
    create_grocery_data()
