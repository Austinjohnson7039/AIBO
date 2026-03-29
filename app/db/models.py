from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.database import Base


class Sale(Base):
    """Represents a single sales transaction line."""

    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    item = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    revenue = Column(Float, nullable=False)
    sale_date = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Sale id={self.id} item={self.item!r} qty={self.quantity} rev={self.revenue} date={self.sale_date}>"


class Inventory(Base):
    """Represents a stock-keeping unit in the café inventory."""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True) # Maps to Item_ID
    item_name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=True)
    item_type = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    supplier = Column(String, nullable=True)
    stock = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)
    cost_price = Column(Float, nullable=False, default=0.0)
    selling_price = Column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return f"<Inventory id={self.id} name={self.item_name!r} stock={self.stock}>"


class Ingredient(Base):
    """Represents a raw grocery ingredient (not for direct sale)."""

    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    current_stock = Column(Float, nullable=False, default=0.0)
    reorder_level = Column(Float, nullable=False, default=10.0)
    unit_cost_inr = Column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return f"<Ingredient id={self.id} name={self.ingredient_name!r} stock={self.current_stock}>"


class Recipe(Base):
    """Maps a Menu Inventory item to its required raw Ingredients."""

    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    menu_item = Column(String, nullable=False) # Maps to Inventory.item_name
    ingredient = Column(String, nullable=False) # Maps to Ingredient.ingredient_name
    quantity_per_unit = Column(Float, nullable=False)
    unit = Column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<Recipe id={self.id} menu={self.menu_item!r} ing={self.ingredient!r} qty={self.quantity_per_unit}>"
