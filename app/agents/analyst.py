"""
analyst.py
──────────
Analyst Agent — handles sales and inventory analysis queries.
Uses SQLAlchemy to pull real-time database context, formatting it 
as tabular text prior to LLM reasoning.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from openai import OpenAI, OpenAIError

from app.config import GROQ_API_KEY
from app.db.database import SessionLocal
from app.db.models import Sale, Inventory

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# ─── Analyst ──────────────────────────────────────────────────────────────────

class AnalystAgent:
    """
    Analyses sales trends, revenue metrics, and inventory levels.
    Pulls structured JSON/CSV data from SQLite via SQLAlchemy and feeds
    it into the LLM as grounding context.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialise the AnalystAgent with an OpenAI client."""
        key = api_key or GROQ_API_KEY
        if key:
            self.client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)
        else:
            self.client = None

    def fetch_db_context(self) -> str:
        """
        Fetches all relevant data from the DB to build the context window.
        
        NOTE: For a production database with millions of rows, we'd use 
        SQL-generation agents (Text-to-SQL) or targeted aggregation queries. 
        Because this is the foundation with a small dataset, we safely 
        extract everything to DataFrames and convert to CSV representations.
        """
        db = SessionLocal()
        try:
            sales = db.query(Sale).all()
            inventory = db.query(Inventory).all()

            # Flatten to dicts
            sales_data = [{"item": s.item, "qty": s.quantity, "rev": s.revenue, "date": s.sale_date.strftime("%Y-%m-%d %H:%M:%S") if s.sale_date else "N/A"} for s in sales]
            inv_data = [
                {
                    "Item_ID": i.id,
                    "Item_Name": i.item_name,
                    "Category": i.category,
                    "Type": i.item_type,
                    "Stock": i.stock,
                    "Reorder_Level": i.reorder_level,
                    "Unit": i.unit,
                    "Cost_Price": i.cost_price,
                    "Selling_Price": i.selling_price,
                    "Supplier": i.supplier
                } for i in inventory
            ]

            sales_df = pd.DataFrame(sales_data) if sales_data else pd.DataFrame()
            inv_df = pd.DataFrame(inv_data) if inv_data else pd.DataFrame()

            # Construct markdown-friendly tabular context
            context_blocks = []

            # ── Python-Computed Analytics (exact, like Excel) ─────────────────
            # Python does all arithmetic. The LLM just reads and presents answers.
            if not sales_df.empty:
                from datetime import datetime, timedelta
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")

                # Define date ranges
                today = now.date()
                week_start = today - timedelta(days=today.weekday())   # Monday
                week_end   = week_start + timedelta(days=6)            # Sunday
                last_week_start = week_start - timedelta(weeks=1)
                last_week_end   = week_start - timedelta(days=1)
                month_start = today.replace(day=1)
                last_month_end = month_start - timedelta(days=1)
                last_month_start = last_month_end.replace(day=1)
                yesterday = today - timedelta(days=1)

                sales_df["date"] = pd.to_datetime(sales_df["date"], errors="coerce")
                sales_df["date_only"] = sales_df["date"].dt.date

                def rev_in(start, end):
                    mask = (sales_df["date_only"] >= start) & (sales_df["date_only"] <= end)
                    return round(sales_df.loc[mask, "rev"].sum(), 2)

                def qty_in(start, end):
                    mask = (sales_df["date_only"] >= start) & (sales_df["date_only"] <= end)
                    return int(sales_df.loc[mask, "qty"].sum())

                def top_items_in(start, end, n=5, by="rev"):
                    mask = (sales_df["date_only"] >= start) & (sales_df["date_only"] <= end)
                    return sales_df[mask].groupby("item")[by].sum().sort_values(ascending=False).head(n)

                # All-time totals
                grand_rev   = round(sales_df["rev"].sum(), 2)
                monthly_rev = sales_df.copy()
                monthly_rev["month"] = sales_df["date"].dt.strftime("%Y-%m")
                monthly_breakdown = monthly_rev.groupby("month")["rev"].sum().round(2).to_dict()

                # Top items all time
                top_qty_all = sales_df.groupby("item")["qty"].sum().sort_values(ascending=False).head(10)
                top_rev_all = sales_df.groupby("item")["rev"].sum().sort_values(ascending=False).head(10)

                lines = [
                    "=== ANALYTICS SUMMARY (computed by Python — 100% accurate) ===",
                    f"Currency: Indian Rupees (₹)  |  Today: {now.strftime('%A, %d %B %Y')} ({today_str})",
                    "",
                    "── TIME-PERIOD REVENUE ──",
                    f"Today ({today}):                  ₹{rev_in(today, today):,.2f}  ({qty_in(today, today)} units)",
                    f"Yesterday ({yesterday}):           ₹{rev_in(yesterday, yesterday):,.2f}  ({qty_in(yesterday, yesterday)} units)",
                    f"This Week ({week_start} to {week_end}):   ₹{rev_in(week_start, week_end):,.2f}  ({qty_in(week_start, week_end)} units)",
                    f"Last Week ({last_week_start} to {last_week_end}): ₹{rev_in(last_week_start, last_week_end):,.2f}  ({qty_in(last_week_start, last_week_end)} units)",
                    f"This Month ({now.strftime('%B %Y')}):       ₹{rev_in(month_start, today):,.2f}  ({qty_in(month_start, today)} units)",
                    f"Last Month ({last_month_start.strftime('%B %Y')}):      ₹{rev_in(last_month_start, last_month_end):,.2f}  ({qty_in(last_month_start, last_month_end)} units)",
                    f"All Time:                          ₹{grand_rev:,.2f}",
                    "",
                    "── MONTHLY BREAKDOWN ──",
                ]
                for month, rev in sorted(monthly_breakdown.items()):
                    lines.append(f"  {month}: ₹{rev:,.2f}")

                lines.append("\n── TOP 10 ITEMS BY QUANTITY SOLD (All Time) ──")
                for item, qty in top_qty_all.items():
                    lines.append(f"  {item}: {int(qty)} units")

                lines.append("\n── TOP 10 ITEMS BY REVENUE (All Time) ──")
                for item, rev in top_rev_all.items():
                    lines.append(f"  {item}: ₹{round(rev, 2):,.2f}")

                lines.append(f"\n── TOP 5 ITEMS THIS WEEK ({week_start} to {week_end}) ──")
                for item, rev in top_items_in(week_start, week_end).items():
                    lines.append(f"  {item}: ₹{round(rev, 2):,.2f}")

                lines.append(f"\n── TOP 5 ITEMS THIS MONTH ──")
                for item, rev in top_items_in(month_start, today).items():
                    lines.append(f"  {item}: ₹{round(rev, 2):,.2f}")

                context_blocks.append("\n".join(lines))
            # ─────────────────────────────────────────────────────────────────

            context_blocks.append("=== INVENTORY TABLE ===")
            if not inv_df.empty:
                context_blocks.append(inv_df.to_csv(index=False))
            else:
                context_blocks.append("No inventory recorded.")

            return "\n".join(context_blocks)
        except Exception as e:
            logger.error("Failed to query DB for analyst context: %s", e)
            return "DATABASE ERROR: Could not retrieve metrics."
        finally:
            db.close()

    def analyze(self, query: str, memory_context: str = "") -> dict:
        """
        Execute an analytical query based entirely on the DB Context.
        
        Args:
            query: The user's analytical question.
            memory_context: Formatted string of conversation history/memory.
            
        Returns:
            A dictionary containing the generated 'answer' and the 'sources' used.
        """
        logger.info("AnalystAgent processing query...")
        
        if not self.client:
            logger.error("AnalystAgent lacks a GROQ_API_KEY.")
            return {
                "answer": "AnalystAgent lacks a GROQ_API_KEY. Cannot run analysis.",
                "sources": []
            }

        # 1. Pull the live DB contents
        db_context = self.fetch_db_context()

        # 2. Prepare the grounding prompt
        system_prompt = (
            "You are an expert Data Analyst AI for a cafe business.\n"
            "Your job is to answer the user's question by carefully reviewing "
            "the provided database context (SALES TABLE and INVENTORY TABLE).\n"
            "The context includes a 'CURRENT DATE & TIME' section — use this to "
            "resolve relative time expressions like 'this week', 'yesterday', 'this month', "
            "'last week', etc. Always derive date ranges from this reference point.\n"
            "The INVENTORY TABLE includes metadata like Category, Type, Cost Price, and Selling Price. "
            "Use these to provide deeper insights like most profitable categories or stock value.\n"
            "Currency: All prices, costs, and revenues are in Indian Rupees (₹).\n"
            "Be precise, reference exact numbers where helpful, and keep your answer concise.\n"
            "If the requested data is not present in the context, explicitly say that."
        )

        user_prompt = f"Question: {query}\n\nDatabase Context:\n{db_context}"
        if memory_context:
            user_prompt = f"Conversation History & Memory:\n{memory_context}\n\n{user_prompt}"

        # 3. Call the LLM
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            answer = response.choices[0].message.content.strip()
            
            return {
                "answer": answer,
                "sources": ["Database: Sales & Inventory Tables"],
                "context_used": db_context
            }
            
        except OpenAIError as e:
            logger.error("OpenAI API Analyst error: %s", e)
            return {
                "answer": "I'm sorry, the language model service is currently unavailable.",
                "sources": ["Database Context Extracted (LLM Error)"],
                "context_used": db_context
            }
        except Exception as e:
            logger.exception("Unexpected analyst error: %s", e)
            return {
                "answer": "I encountered an unexpected error while performing the analysis.",
                "sources": [],
                "context_used": ""
            }
