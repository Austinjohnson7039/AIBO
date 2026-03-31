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

def record_sale_op(tenant_id: int, item: str, quantity: int, revenue: float) -> bool:
    """Record a single sale line in the cloud database."""
    db = SessionLocal()
    try:
        new_sale = Sale(
            tenant_id=tenant_id,
            item=item,
            quantity=quantity,
            revenue=revenue,
            sale_date=datetime.utcnow()
        )
        db.add(new_sale)
        
        # Also update inventory stock accordingly if the item exists (Exact match, Case-Insensitive)
        inv_item = db.query(Inventory).filter(Inventory.tenant_id == tenant_id, Inventory.item_name.ilike(item)).first()
        if inv_item:
            inv_item.stock = max(0, inv_item.stock - quantity)
            logger.info("Stock for %s reduced by %d. New Stock: %d", item, quantity, inv_item.stock)
            
        db.commit()
        return True
    except Exception as e:
        logger.error("Failed to record sale: %s", e)
        db.rollback()
        return False
    finally:
        db.close()

def add_inventory_op(tenant_id: int, item_name: str, quantity: int, reorder_level: int = 10, category: str = "Uncategorized") -> bool:
    """Add stock to an existing item or create a new inventory entry."""
    db = SessionLocal()
    try:
        # Prevent SQL overlapping substring matching vectors: Exact Match Only
        inv_item = db.query(Inventory).filter(Inventory.tenant_id == tenant_id, Inventory.item_name.ilike(item_name)).first()
        if inv_item:
            inv_item.stock += quantity
            logger.info("Updated existing inventory: %s (+%d)", item_name, quantity)
        else:
            # For a brand new item, rely entirely on the DB explicitly for Primary Key Auto-Incrementation.
            # Do NOT manually search `last_item` + 1 (Fatal Multi-Tenant collision risk).
            new_item = Inventory(
                tenant_id=tenant_id,
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
            logger.info("Added NEW inventory item: %s (%d) organically to the cloud backend.", item_name, quantity)
            
        db.commit()
        return True
    except Exception as e:
        logger.error("Failed to add inventory: %s", e)
        db.rollback()
        return False
    finally:
        db.close()

def update_inventory_op(tenant_id: int, item_name: str, updates: dict) -> bool:
    """Perform absolute edits (overwrites) on an existing inventory item."""
    db = SessionLocal()
    try:
        # Match identical item ONLY (ignores pure substring similarities)
        inv_item = db.query(Inventory).filter(Inventory.tenant_id == tenant_id, Inventory.item_name.ilike(item_name)).first()
        if not inv_item:
            logger.warning("Attempted to update non-existent physical item: %s", item_name)
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
