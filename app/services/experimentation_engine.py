from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from app.services.stock_engine import stock_engine
from openai import OpenAI
from app.config import GROQ_API_KEY

class ExperimentationEngine:
    def __init__(self):
        self.client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"

    def generate_strategy(self, db: Session, tenant_id: int):
        grocery, recipes, sales, inv_df = stock_engine.load_data(db, tenant_id)
        
        if sales.empty:
            return {
                "status": "warning", 
                "message": "Not enough sales data to generate an experiment."
            }
            
        sales["date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
        sales["date_only"] = sales["date"].dt.date
        top_items = sales.groupby("item")["quantity"].sum().sort_values(ascending=False)
        
        top_3 = top_items.head(3).to_dict()
        bottom_3 = top_items.tail(3).to_dict()
        
        prompt = (
            f"You are the AI Cafe Strategy Engine. Based on recent sales, we want to create a highly automated, data-driven promotion strategy to increase revenue.\n\n"
            f"Top Selling Items & Quantities:\n{top_3}\n\n"
            f"Slowest Selling Items & Quantities:\n{bottom_3}\n\n"
            "Task: Generate exactly ONE 'Combo Offer' or 'Discount Strategy' that pairs a fast-moving item with a slow-moving item to clear inventory and boost profits. "
            "Return the output strictly in a simple Markdown Table containing 'Offer Name', 'Items Included', and 'Expected Impact'. Do NOT use asterisks (*) for formatting. Keep it short!"
        )
        
        if not self.client:
            return {"status": "error", "message": "API key not configured."}
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            strategy = response.choices[0].message.content.strip()
            return {"status": "success", "strategy": strategy}
        except Exception as e:
            return {"status": "error", "message": str(e)}

experimentation_engine = ExperimentationEngine()
