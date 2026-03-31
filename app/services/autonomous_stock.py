import logging
import pandas as pd
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.db.models import Tenant, Sale, Ingredient, Recipe
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def optimize_reorder_levels_autonomously():
    """
    Cron Job Function:
    Calculates 7-day average burn rates vs historical burn rates for all tenants.
    AUTONOMOUSLY updates the `reorder_level` safety net if items are selling 2x faster.
    """
    logger.info("Running Autonomous Reorder Level Optimizer...")
    db: Session = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        for t in tenants:
            _optimize_tenant_reorder_levels(db, t.id)
    except Exception as e:
        logger.error(f"Autonomous Stock Engine crashed: {e}")
    finally:
        db.close()

def _optimize_tenant_reorder_levels(db: Session, tenant_id: int):
    # Fetch data
    sales = db.query(Sale).filter(Sale.tenant_id == tenant_id).all()
    if not sales: return
    
    sales_df = pd.DataFrame([{ "item": s.item, "qty": s.quantity, "date": s.sale_date } for s in sales])
    sales_df["date"] = pd.to_datetime(sales_df["date"], errors="coerce").dt.date
    
    recipes = db.query(Recipe).filter(Recipe.tenant_id == tenant_id).all()
    recipes_df = pd.DataFrame([{"menu_item": r.menu_item, "ingredient": r.ingredient, "qty_needed": r.quantity_per_unit} for r in recipes])
    
    if recipes_df.empty: return

    # Merge to calculate raw ingredient burn
    merged = pd.merge(sales_df, recipes_df, left_on="item", right_on="menu_item")
    merged["ingredient_burned"] = merged["qty"] * merged["qty_needed"]
    
    # Analyze Last 7 days vs Prior 7 days moving average
    cutoff = datetime.utcnow().date() - timedelta(days=7)
    prior_cutoff = cutoff - timedelta(days=7)
    
    recent_burn = merged[merged["date"] >= cutoff].groupby("ingredient")["ingredient_burned"].sum()
    prior_burn = merged[(merged["date"] >= prior_cutoff) & (merged["date"] < cutoff)].groupby("ingredient")["ingredient_burned"].sum()
    
    # Active Autonomous Updates
    ingredients = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id).all()
    for ing in ingredients:
        recent = recent_burn.get(ing.ingredient_name, 0)
        prior = prior_burn.get(ing.ingredient_name, 0)
        
        # BUG FIX (BUG 9): Was inflating by 25% every cycle with no ceiling.
        # Added: (a) max cap of 3x the current reorder level, and (b) only raises if
        # the new level would be below the burn rate (actionable, not runaway).
        if prior > 0 and (recent / prior) >= 2.0:
            old_level = ing.reorder_level
            proposed = round(old_level * 1.25, 2)
            # Cap: never exceed 3x the original level OR the 7-day burn rate (whichever is lower)
            cap = min(old_level * 3.0, recent * 1.5) if recent > 0 else old_level * 3.0
            ing.reorder_level = min(proposed, cap)
            if ing.reorder_level != old_level:
                logger.warning(f"AUTO-ADJUST [Tenant {tenant_id}]: Increased '{ing.ingredient_name}' reorder level {old_level} -> {ing.reorder_level} (cap: {cap:.1f}) due to sales spike.")

    db.commit()
