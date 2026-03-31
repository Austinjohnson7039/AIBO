"""
helpers.py
──────────
Utility functions for database initialisation and CSV data loading.
These are intentionally kept side-effect free when imported;
call init_db() and load_data() explicitly (e.g. from a startup handler).
"""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.db.models import Inventory, Sale

logger = logging.getLogger(__name__)

# Resolve the `data/` directory relative to the project root
# __file__  → app/utils/helpers.py
# .parents[2] → project root (ai-cafe-manager/)
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# ─── Database Initialisation ──────────────────────────────────────────────────


def init_db() -> None:
    """Create all tables defined in the ORM metadata (idempotent)."""
    # Import models so SQLAlchemy registers them on the metadata object
    import app.db.models  # noqa: F401  (side-effect import)

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialised.")


# ─── CSV → DB Loaders ─────────────────────────────────────────────────────────


def _load_sales(db: Session) -> None:
    """Insert sales rows from sales.csv if the table is empty."""
    if db.query(Sale).count() > 0:
        logger.info("Sales table already populated — skipping.")
        return

    csv_path = _DATA_DIR / "sales.csv"
    df = pd.read_csv(csv_path)

    records = [
        Sale(
            item=row["item"],
            quantity=int(row["quantity"]),
            revenue=float(row["revenue"]),
            sale_date=datetime.fromisoformat(row["sale_date"]),
        )
        for _, row in df.iterrows()
    ]

    db.bulk_save_objects(records)
    db.commit()
    logger.info("Loaded %d sales records from %s.", len(records), csv_path)


def _load_inventory(db: Session) -> None:
    """Insert inventory rows from
     inventory.csv if the table is empty."""
    if db.query(Inventory).count() > 0:
        logger.info("Inventory table already populated — skipping.")
        return

    csv_path = _DATA_DIR / "inventory_v2.csv"
    df = pd.read_csv(csv_path)

    records = [
        Inventory(
            # BUG FIX (BUG 17): Was manually setting `id` from CSV which bypasses
            # auto-increment and causes PK collisions with new inserts.
            item_name=row["Item_Name"],
            category=row.get("Category"),
            item_type=row.get("Type"),
            unit=row.get("Unit"),
            supplier=row.get("Supplier"),
            stock=int(row["Stock"]),
            reorder_level=int(row["Reorder_Level"]),
            cost_price=float(row.get("Cost_Price", 0.0)),
            selling_price=float(row.get("Selling_Price", 0.0)),
        )
        for _, row in df.iterrows()
    ]

    db.bulk_save_objects(records)
    db.commit()
    logger.info("Loaded %d inventory records from %s.", len(records), csv_path)


def load_data() -> None:
    """Top-level entry point: load all CSV seed data into the database."""
    db: Session = SessionLocal()
    try:
        _load_sales(db)
        _load_inventory(db)
    except Exception:
        db.rollback()
        logger.exception("Failed to load CSV data into the database.")
        raise
    finally:
        db.close()
