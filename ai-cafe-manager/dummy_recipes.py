import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.db.models import Tenant, Ingredient, Recipe

db = SessionLocal()
tenants = db.query(Tenant).all()

for t in tenants:
    # 1. Add Ingredients
    existing_ing = db.query(Ingredient).filter(Ingredient.tenant_id == t.id).count()
    if existing_ing == 0:
        ingredients = [
            Ingredient(tenant_id=t.id, ingredient_name="Potatoes", category="Vegetables", unit="kg", current_stock=2.5, reorder_level=5.0, unit_cost_inr=30.0),
            Ingredient(tenant_id=t.id, ingredient_name="Burger Bun", category="Bakery", unit="pcs", current_stock=12.0, reorder_level=20.0, unit_cost_inr=5.0),
            Ingredient(tenant_id=t.id, ingredient_name="Veg Patty", category="Frozen", unit="pcs", current_stock=8.0, reorder_level=15.0, unit_cost_inr=15.0),
            Ingredient(tenant_id=t.id, ingredient_name="Coffee Beans", category="Pantry", unit="kg", current_stock=0.5, reorder_level=2.0, unit_cost_inr=800.0),
            Ingredient(tenant_id=t.id, ingredient_name="Milk", category="Dairy", unit="L", current_stock=3.0, reorder_level=5.0, unit_cost_inr=60.0),
            Ingredient(tenant_id=t.id, ingredient_name="Chocolate Syrup", category="Pantry", unit="ml", current_stock=200.0, reorder_level=500.0, unit_cost_inr=0.5),
        ]
        db.add_all(ingredients)
        db.commit()

    # 2. Add Recipes
    existing_rec = db.query(Recipe).filter(Recipe.tenant_id == t.id).count()
    if existing_rec == 0:
        recipes = [
            Recipe(tenant_id=t.id, menu_item="Fries", ingredient="Potatoes", quantity_per_unit=0.2, unit="kg"),
            Recipe(tenant_id=t.id, menu_item="Burger", ingredient="Burger Bun", quantity_per_unit=1.0, unit="pcs"),
            Recipe(tenant_id=t.id, menu_item="Burger", ingredient="Veg Patty", quantity_per_unit=1.0, unit="pcs"),
            Recipe(tenant_id=t.id, menu_item="Cold Coffee", ingredient="Coffee Beans", quantity_per_unit=0.015, unit="kg"),
            Recipe(tenant_id=t.id, menu_item="Cold Coffee", ingredient="Milk", quantity_per_unit=0.25, unit="L"),
            Recipe(tenant_id=t.id, menu_item="Cold Coffee", ingredient="Chocolate Syrup", quantity_per_unit=30.0, unit="ml"),
        ]
        db.add_all(recipes)
        db.commit()

print("Ingredient and Recipe Data populated!")
