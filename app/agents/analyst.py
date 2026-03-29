"""
analyst.py
──────────
Analyst Agent — handles sales and inventory analysis queries.
Uses SQLAlchemy to pull real-time database context, formatting it 
as tabular text prior to LLM reasoning.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from openai import OpenAI, OpenAIError

from app.config import GROQ_API_KEY
from app.db.database import SessionLocal
from app.db.models import Sale, Ingredient, Employee, Attendance, Wastage

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# ─── Analyst ──────────────────────────────────────────────────────────────────

class AnalystAgent:
    """
    Analyses sales trends, revenue metrics, and inventory levels.
    Pulls structured data from the DB and feeds pre-computed analytics
    into the LLM as grounding context.
    """

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or GROQ_API_KEY
        if key:
            self.client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)
        else:
            self.client = None

    def fetch_db_context(self, tenant_id: int) -> str:
        """
        Fetches tenant-specific data and builds a compact, pre-computed
        analytics context for the LLM. All math is done in Python.
        """
        db = SessionLocal()
        try:
            sales = db.query(Sale).filter(Sale.tenant_id == tenant_id).all()
            grocery = db.query(Ingredient).filter(Ingredient.tenant_id == tenant_id).all()
            employees = db.query(Employee).filter(Employee.tenant_id == tenant_id).all()
            wastage = db.query(Wastage).filter(Wastage.tenant_id == tenant_id).order_by(Wastage.logged_at.desc()).limit(20).all()

            # ── Build DataFrames ──────────────────────────────────────────
            sales_data = []
            for s in sales:
                sales_data.append({
                    "item": s.item,
                    "qty": s.quantity,
                    "rev": s.revenue,
                    "date": s.sale_date.strftime("%Y-%m-%d %H:%M:%S") if s.sale_date else "N/A"
                })

            gro_data = []
            for g in grocery:
                gro_data.append({
                    "Name": g.ingredient_name,
                    "Category": g.category,
                    "Stock": g.current_stock,
                    "Reorder_At": g.reorder_level,
                    "Unit": g.unit,
                    "Cost_per_unit": g.unit_cost_inr
                })

            sales_df = pd.DataFrame(sales_data) if sales_data else pd.DataFrame()
            gro_df = pd.DataFrame(gro_data) if gro_data else pd.DataFrame()

            # ── Temporal Grounding ────────────────────────────────────────
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            context_blocks = [
                "=== CURRENT DATE & TIME ===",
                f"Server Time (IST): {now_str}",
                f"Today: {now.strftime('%A, %d %B %Y')}",
                ""
            ]

            # ── Pre-Computed Analytics ────────────────────────────────────
            if not sales_df.empty:
                sales_df["date"] = pd.to_datetime(sales_df["date"], errors="coerce")
                sales_df["date_only"] = sales_df["date"].dt.date

                # Use real 'now' for time-based filtering
                today = now.date()
                yesterday = today - timedelta(days=1)
                week_start = today - timedelta(days=today.weekday())
                week_end = week_start + timedelta(days=6)
                month_start = today.replace(day=1)
                last_month_end = month_start - timedelta(days=1)
                last_month_start = last_month_end.replace(day=1)

                # Also compute based on when data actually exists
                data_min = sales_df["date_only"].min()
                data_max = sales_df["date_only"].max()

                def rev_in(start, end):
                    mask = (sales_df["date_only"] >= start) & (sales_df["date_only"] <= end)
                    return round(sales_df.loc[mask, "rev"].sum(), 2)

                def qty_in(start, end):
                    mask = (sales_df["date_only"] >= start) & (sales_df["date_only"] <= end)
                    return int(sales_df.loc[mask, "qty"].sum())

                grand_rev = round(sales_df["rev"].sum(), 2)
                grand_qty = int(sales_df["qty"].sum())

                # Monthly breakdown
                monthly_rev = sales_df.copy()
                monthly_rev["month"] = sales_df["date"].dt.strftime("%Y-%m")
                monthly_breakdown = monthly_rev.groupby("month")["rev"].sum().round(2).to_dict()

                # Top items
                top_items_rev = sales_df.groupby("item")["rev"].sum().sort_values(ascending=False).head(10)
                top_items_qty = sales_df.groupby("item")["qty"].sum().sort_values(ascending=False).head(10)

                lines = [
                    "=== SALES ANALYTICS (pre-computed, 100% accurate) ===",
                    f"Data range: {data_min} to {data_max}",
                    f"Total sales records: {len(sales_df)}",
                    "",
                    "── REVENUE BY PERIOD ──",
                    f"Today ({today}): ₹{rev_in(today, today):,.2f} ({qty_in(today, today)} items)",
                    f"Yesterday ({yesterday}): ₹{rev_in(yesterday, yesterday):,.2f}",
                    f"This Week ({week_start} → {week_end}): ₹{rev_in(week_start, week_end):,.2f}",
                    f"This Month ({now.strftime('%B %Y')}): ₹{rev_in(month_start, today):,.2f}",
                    f"Last Month ({last_month_start.strftime('%B %Y')}): ₹{rev_in(last_month_start, last_month_end):,.2f}",
                    f"ALL TIME TOTAL: ₹{grand_rev:,.2f} ({grand_qty} items sold)",
                    "",
                    "── MONTHLY BREAKDOWN ──",
                ]
                for month, rev in sorted(monthly_breakdown.items()):
                    lines.append(f"  {month}: ₹{rev:,.2f}")

                lines.append("\n── TOP 10 ITEMS BY REVENUE ──")
                for item, rev in top_items_rev.items():
                    lines.append(f"  {item}: ₹{rev:,.2f}")

                lines.append("\n── TOP 10 ITEMS BY QUANTITY ──")
                for item, qty in top_items_qty.items():
                    lines.append(f"  {item}: {int(qty)} sold")

                context_blocks.append("\n".join(lines))
            else:
                context_blocks.append("=== SALES ===\nNo sales recorded yet.")

            # ── Grocery / Ingredients ─────────────────────────────────────
            context_blocks.append("")
            context_blocks.append("=== INGREDIENTS (Grocery Stock) ===")
            if not gro_df.empty:
                context_blocks.append(gro_df.to_string(index=False))
            else:
                context_blocks.append("No ingredients in stock.")

            # ── Staff / Employees ──────────────────────────────────────────
            context_blocks.append("")
            context_blocks.append("=== STAFF & EMPLOYEES ===")
            if employees:
                staff_lines = []
                for emp in employees:
                    # check if clocked in
                    att = db.query(Attendance).filter(
                        Attendance.tenant_id == tenant_id, 
                        Attendance.employee_id == emp.id
                    ).order_by(Attendance.id.desc()).first()
                    
                    status = "Not clocked in"
                    if att and att.check_in and not att.check_out:
                        status = "Currently Working (Clocked In)"
                        
                    staff_lines.append(f"- {emp.name} (Role: {emp.role}, Status: {status})")
                context_blocks.append("\n".join(staff_lines))
            else:
                context_blocks.append("No staff recorded.")

            # ── Recent Wastage / Expiry ────────────────────────────────────
            context_blocks.append("")
            context_blocks.append("=== RECENT WASTAGE & EXPIRY LOGS (Last 20) ===")
            if wastage:
                was_lines = []
                for w in wastage:
                    was_lines.append(f"- {w.logged_at.strftime('%Y-%m-%d')}: {w.quantity}x {w.item_name} ({w.reason}) — Loss: ₹{w.loss_amount}")
                context_blocks.append("\n".join(was_lines))
            else:
                context_blocks.append("No recent wastage logged.")

            return "\n".join(context_blocks)

        except Exception as e:
            logger.error("Failed to query DB for analyst context: %s", e)
            return f"DATABASE ERROR: {str(e)}"
        finally:
            db.close()

    def analyze(self, query: str, tenant_id: int, memory_context: str = "") -> dict:
        """Execute an analytical query grounded in the tenant's live DB data."""
        logger.info("AnalystAgent processing query for tenant %s...", tenant_id)

        if not self.client:
            return {
                "answer": "AI service is not configured. Please set the GROQ_API_KEY.",
                "sources": []
            }

        # 1. Pull live DB context
        db_context = self.fetch_db_context(tenant_id)

        # 2. System prompt — instructs the LLM to use pre-computed data
        system_prompt = (
            "You are AIBO, a senior Business Intelligence Consultant specializing in food & beverage operations.\n"
            "Your job is to deliver precise, data-backed analysis reports using ONLY the database context provided.\n\n"

            "CRITICAL DATA RULES:\n"
            "1. Information on 'SALES', 'INGREDIENTS', 'STAFF & EMPLOYEES' (including Attendance), and 'RECENT WASTAGE' is explicitly provided in the Database Context. Read it thoroughly.\n"
            "2. The 'SALES ANALYTICS' section has pre-computed, 100% accurate figures. Use them verbatim. Never estimate.\n"
            "3. Use the 'CURRENT DATE & TIME' to correctly resolve 'today', 'this week', 'this month'.\n"
            "4. All currency is Indian Rupees (₹). Format with commas (e.g., ₹1,23,456.78).\n"
            "5. Never fabricate data. If 'No staff recorded' is given, then say 0 staff. If data is unavailable, state it precisely in one line.\n\n"

            "FORMATTING RULES — ALWAYS follow this structure:\n"
            "1. EXTREMELY CONCISE. Use bullet points heavily. NO LONG PARAGRAPHS.\n"
            "2. Use **bold** for key metrics, item names, and action items.\n"
            "3. Omit marketing fluff. Go straight to the answer.\n"
            "4. End with a crisp **Bottom Line** one-liner under `---`.\n"
        )

        user_prompt = f"Question: {query}\n\nDatabase Context:\n{db_context}"
        if memory_context:
            user_prompt = f"Recent conversation:\n{memory_context}\n\n{user_prompt}"

        # 3. Call LLM with token limit to prevent overflow
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2048
            )
            answer = response.choices[0].message.content.strip()

            return {
                "answer": answer,
                "sources": ["Sales & Inventory Database"],
            }

        except OpenAIError as e:
            logger.error("Groq API error: %s", e)
            return {
                "answer": "I'm having trouble connecting to the AI service right now. Please try again in a moment.",
                "sources": [],
            }
        except Exception as e:
            logger.exception("Unexpected analyst error: %s", e)
            return {
                "answer": "Something went wrong while analyzing your data. Please try again.",
                "sources": [],
            }
