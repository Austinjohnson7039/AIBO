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
