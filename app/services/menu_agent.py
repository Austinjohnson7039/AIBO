import python_weather
import json
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import Inventory, Tenant
from openai import AsyncOpenAI, OpenAIError
from app.config import GROQ_API_KEY

logger = logging.getLogger(__name__)

LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

class MenuAgent:
    """The Intelligent Dynamic Pricing Engine for AIBO."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or GROQ_API_KEY
        if key:
            self.client = AsyncOpenAI(api_key=key, base_url=GROQ_BASE_URL)
        else:
            self.client = None

    async def get_weather(self, city: str):
        """Fetches live weather data for the tenant's location."""
        try:
            async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
                weather = await client.get(city)
                return {
                    "temp": (weather.temperature - 32) * 5/9, # Convert to Celsius
                    "description": weather.description,
                    "kind": str(weather.kind)
                }
        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            return {"temp": 25, "description": "Clear", "kind": "Sunny"}

    async def generate_recommendations(self, db: Session, tenant: Tenant) -> List[Dict]:
        """Analyzes weather and inventory using LLM to suggest pricing pivots."""
        weather = await self.get_weather(tenant.location)
        temp = weather["temp"]
        
        # Pull tenant inventory
        items = db.query(Inventory).filter(Inventory.tenant_id == tenant.id).all()
        
        if not items:
            return []

        if not self.client:
            logger.warning("No LLM client configured for MenuAgent.")
            return []

        inventory_context = "Available Menu Items:\n"
        for item in items:
            inventory_context += f"- {item.item_name}: Stock={item.stock}, Cost=₹{item.cost_price}, Current Price=₹{item.selling_price}\n"

        system_prompt = (
            "You are AIBO's dynamic pricing intelligence engine. You analyze local weather conditions and current "
            "stock inventory to recommend optimized pricing strategies (surgers or discounts) for a café menu.\n\n"
            "You MUST return EXACTLY a JSON object with a 'recommendations' array. Do not include markdown formatting like ```json or anything outside the JSON object.\n"
            "Each object inside the 'recommendations' array must have:\n"
            "  \"item\" (string) : Name of the contextual item\n"
            "  \"current_price\" (number) : The current price\n"
            "  \"suggested_price\" (number) : The new optimized price\n"
            "  \"reason\" (string) : A highly professional 1-sentence business rationale citing weather or overstock.\n"
            "  \"type\" (string) : Either \"SURGE\" or \"DISCOUNT\"\n"
            "  \"confidence\" (number) : A number between 70 and 99"
        )

        user_prompt = (
            f"Location: {tenant.location}\n"
            f"Current Weather: {temp:.1f}°C, {weather['description']}\n\n"
            f"{inventory_context}\n\n"
            "Select 3 to 4 items that urgently need pricing adjustments. Provide robust business reasoning."
        )

        try:
            response = await self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            # Failsafe in case Groq includes markdown
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            data = json.loads(content)
            return data.get("recommendations", [])
            
        except Exception as e:
            logger.exception("AI Menu Generation Failed: %s", e)
            return []

menu_agent = MenuAgent()
