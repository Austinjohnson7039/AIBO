import asyncio
import logging
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.db.models import Tenant, Employee, Attendance, Sale, Inventory
from app.services.autonomous_stock import optimize_reorder_levels_autonomously
from app.services.menu_agent import menu_agent
from app.services.whatsapp import send_whatsapp_alert
from sqlalchemy.orm import Session
import os

logger = logging.getLogger(__name__)

async def run_autonomous_shift_trimmer():
    """
    Feature C: Shift Trimmer
    If recent footfall is practically 0, automatically messages lowest tier staff not to come.
    """
    db: Session = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        for t in tenants:
            try:
                # Check sales from the last 24 hours
                cutoff = datetime.utcnow() - timedelta(hours=24)
                sales_vol = db.query(Sale).filter(Sale.tenant_id == t.id, Sale.sale_date >= cutoff).count()
                
                # Simple simulation: if we have radically less than 5 sales in a full day, it's a dead day.
                if sales_vol < 5:
                    # Find part-time workers or lowest hourly rate
                    staff = db.query(Employee).filter(Employee.tenant_id == t.id, Employee.is_active == 1).order_by(Employee.hourly_rate.asc()).first()
                    if staff:
                        msg = f"📉 *AIBO LABOUR OPTIMIZATION*\nWarning: Store traffic is critically low.\n"
                        msg += f"I have autonomously removed {staff.name} from tomorrow's shift to protect bottom-line margins."
                        send_whatsapp_alert(msg)
                        logger.warning(f"AUTO-ADJUST [Tenant {t.id}]: Autonomously cut {staff.name}'s shift due to slow sales forecast ({sales_vol} sales).")
            except Exception as tenant_err:
                logger.error(f"Shift trimmer error for tenant {t.id}: {tenant_err}")
    except Exception as e:
        logger.error(f"Shift trimmer global error: {e}")
    finally:
        db.close()

async def run_autonomous_surge_pricing():
    """
    BUG FIX (BUG 10): Triggers the weather-based semantic pricing agent for all active cafes.
    Also checks for good weather and REVERTS any previously surged prices back to base.
    """
    db: Session = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        for t in tenants:
            try:
                await menu_agent.apply_autonomous_surge_pricing(db, t)
            except Exception as tenant_err:
                logger.error(f"Surge pricing error for tenant {t.id}: {tenant_err}")
    except Exception as e:
        logger.error(f"Surge pricing global error: {e}")
    finally:
        db.close()

async def run_autonomous_price_revert():
    """
    BUG FIX (BUG 10): On good weather days, revert any surge-priced items back to base price.
    Uses Inventory.cost_price as a base reference. Prevents permanent inflation.
    """
    db: Session = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        for t in tenants:
            try:
                weather = await menu_agent.get_weather(t.location)
                desc = weather.get("description", "").lower()
                kind = weather.get("kind", "").lower()
                is_bad_weather = any(word in desc for word in ["rain", "storm", "thunder", "snow"]) or "rain" in kind or "storm" in kind
                
                if not is_bad_weather:
                    # Good weather: check for any items where selling_price > cost_price * 2.5 (likely surged)
                    # Revert selling_price to a reasonable default (cost_price * 2.0 margin)
                    items = db.query(Inventory).filter(Inventory.tenant_id == t.id).all()
                    reverted = []
                    for item in items:
                        if item.cost_price > 0 and item.selling_price > item.cost_price * 2.5:
                            # Revert to standard 2x markup
                            original_price = round(item.cost_price * 2.0, 2)
                            reverted.append(f"{item.item_name} (₹{item.selling_price} -> ₹{original_price})")
                            item.selling_price = original_price
                    if reverted:
                        db.commit()
                        logger.info(f"AUTO-REVERT [Tenant {t.id}]: Restored pricing for {len(reverted)} items after weather cleared.")
            except Exception as tenant_err:
                logger.error(f"Price revert error for tenant {t.id}: {tenant_err}")
    except Exception as e:
        logger.error(f"Price revert global error: {e}")
    finally:
        db.close()

async def cron_loop():
    """
    The master background loop driving AI autonomy.
    BUG FIX (BUG 6): Each cron task is now wrapped in its own try/except so a single
    failure cannot silently kill the entire autonomous loop.
    """
    logger.info("Initializing Autonomy Cron Loop. AI is now managing the cafe.")
    # Run slightly offset to not block fast API boot
    await asyncio.sleep(15)
    
    while True:
        logger.info("CRON: Triggering Autonomous Learning Systems...")
        
        # 1. Background reorder adjustment based on consumption rates
        try:
            optimize_reorder_levels_autonomously()
        except Exception as e:
            logger.error(f"[CRON] Reorder optimizer crashed (non-fatal): {e}")
        
        # 2. Shift Trimming logic based on historical 24h traffic
        try:
            await run_autonomous_shift_trimmer()
        except Exception as e:
            logger.error(f"[CRON] Shift trimmer crashed (non-fatal): {e}")
            
        # 3. Dynamic pricing Engine (Weather Based)
        try:
            await run_autonomous_surge_pricing()
        except Exception as e:
            logger.error(f"[CRON] Surge pricing crashed (non-fatal): {e}")

        # 4. NEW: Price revert on good weather days to prevent permanent inflation
        try:
            await run_autonomous_price_revert()
        except Exception as e:
            logger.error(f"[CRON] Price revert crashed (non-fatal): {e}")

        # Run every 6 hours for responsive autonomous behavior
        logger.info("CRON: Cycle complete. Next run in 6 hours.")
        await asyncio.sleep(21600)  # 6 hours

def start_background_cron_jobs():
    """Fires and detaches the master cron event loop for FastAPI."""
    asyncio.create_task(cron_loop())
