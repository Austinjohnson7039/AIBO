"""
ops_helpers.py
───────────────
Functions to modify the database state in a single transaction.
Used for "agentic" operations (Add to Inventory, Record Sale).
"""

import logging
from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import Sale, Inventory

logger = logging.getLogger(__name__)

def record_sale_op(item: str, quantity: int, revenue: float) -> bool:
    """Record a single sale line in the cloud database."""
    db = SessionLocal()
    try:
        new_sale = Sale(
            item=item,
            quantity=quantity,
            revenue=revenue,
            sale_date=datetime.utcnow()
        )
        db.add(new_sale)
        
        # Also update inventory stock accordingly if the item exists
        inv_item = db.query(Inventory).filter(Inventory.item_name.like(f"%{item}%")).first()
        if inv_item:
            inv_item.stock -= quantity
            logger.info("Stock for %s reduced by %d.", item, quantity)
            
        db.commit()
        return True
    except Exception as e:
        logger.error("Failed to record sale: %s", e)
        db.rollback()
        return False
    finally:
        db.close()

def add_inventory_op(item_name: str, quantity: int, reorder_level: int = 10, category: str = "Uncategorized") -> bool:
    """Add stock to an existing item or create a new inventory entry."""
    db = SessionLocal()
    try:
        inv_item = db.query(Inventory).filter(Inventory.item_name.like(f"%{item_name}%")).first()
        if inv_item:
            inv_item.stock += quantity
            logger.info("Updated existing inventory: %s (+%d)", item_name, quantity)
        else:
            # For a brand new item, we generate a new ID (highest + 1)
            last_item = db.query(Inventory).order_by(Inventory.id.desc()).first()
            new_id = (last_item.id + 1) if last_item else 1
            
            new_item = Inventory(
                id=new_id,
                item_name=item_name,
                stock=quantity,
                reorder_level=reorder_level,
                category=category,
                item_type="General",
                unit="pcs",
                cost_price=0.0,
                selling_price=0.0
            )
            db.add(new_item)
            logger.info("Added NEW inventory item: %s (%d) with ID %d", item_name, quantity, new_id)
            
        db.commit()
        return True
    except Exception as e:
        logger.error("Failed to add inventory: %s", e)
        db.rollback()
        return False
    finally:
        db.close()

def update_inventory_op(item_name: str, updates: dict) -> bool:
    """Perform absolute edits (overwrites) on an existing inventory item."""
    db = SessionLocal()
    try:
        inv_item = db.query(Inventory).filter(Inventory.item_name.like(f"%{item_name}%")).first()
        if not inv_item:
            logger.warning("Attempted to update non-existent item: %s", item_name)
            return False
            
        # Dynamically apply updates
        for field, value in updates.items():
            if hasattr(inv_item, field) and value is not None:
                setattr(inv_item, field, value)
                logger.info("Updated %s: %s -> %s", item_name, field, value)
                
        db.commit()
        return True
    except Exception as e:
        logger.error("Failed to update inventory: %s", e)
        db.rollback()
        return False
    finally:
        db.close()
