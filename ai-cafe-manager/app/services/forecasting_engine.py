import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

from app.services.stock_engine import stock_engine

class ForecastingEngine:
    def __init__(self):
        pass

    def get_inventory_forecast(self, lookback_days=30, forecast_days=7, safety_buffer=0.15):
        """
        Calculates ingredient burn rates and predicts future needs.
        """
        grocery_df, recipes_df, sales_df = stock_engine.load_data()
        
        if sales_df.empty:
            return {"error": "No sales data found for forecasting."}

        # 1. Calculate Daily Consumption for each ingredient
        sales_df['sale_date'] = pd.to_datetime(sales_df['sale_date'])
        recent_sales = sales_df[sales_df['sale_date'] >= (datetime.utcnow() - timedelta(days=lookback_days))]
        
        if recent_sales.empty:
            return {"error": f"No sales data found in the last {lookback_days} days."}

        # Merge sales with recipes to find ingredient usage
        usage_merged = pd.merge(recent_sales, recipes_df, left_on='item', right_on='menu_item')
        usage_merged['total_used'] = usage_merged['quantity'] * usage_merged['quantity_per_unit']
        
        # Aggregate usage by ingredient
        usage_agg = usage_merged.groupby('ingredient')['total_used'].sum().reset_index()
        
        # Calculate daily burn rate
        usage_agg['daily_burn_rate'] = usage_agg['total_used'] / lookback_days
        
        # 2. Join with Grocery Stock to calculate "Runway"
        forecast_df = pd.merge(grocery_df, usage_agg, left_on='ingredient_name', right_on='ingredient', how='left')
        forecast_df['daily_burn_rate'] = forecast_df['daily_burn_rate'].fillna(0)
        
        # Days of stock left: current_stock / daily_burn_rate
        # Use 0.0001 to avoid division by zero
        forecast_df['runway_days'] = forecast_df['current_stock'] / (forecast_df['daily_burn_rate'] + 0.0001)
        
        # 3. Smart Shopping List
        # Quantity needed = (Daily Burn * Forecast Days) * (1 + Safety Buffer) - Current Stock
        forecast_df['needed_for_period'] = (forecast_df['daily_burn_rate'] * forecast_days) * (1 + safety_buffer)
        forecast_df['to_buy'] = forecast_df['needed_for_period'] - forecast_df['current_stock']
        forecast_df['to_buy'] = forecast_df['to_buy'].apply(lambda x: max(0, x))
        
        # Format for UI
        shopping_list = forecast_df[forecast_df['to_buy'] > 0][['ingredient_name', 'to_buy', 'unit']].to_dict('records')
        runway_metrics = forecast_df[['ingredient_name', 'runway_days', 'current_stock', 'unit']].to_dict('records')
        
        return {
            "shopping_list": shopping_list,
            "runway_metrics": runway_metrics,
            "forecast_period_days": forecast_days
        }

    def get_marketing_insights(self):
        """
        Analyzes sales momentum (Week-over-Week) to suggest promotions.
        """
        _, _, sales_df = stock_engine.load_data()
        
        if sales_df.empty or len(sales_df) < 5:
            return {"error": "Not enough sales data for trend analysis."}

        sales_df['sale_date'] = pd.to_datetime(sales_df['sale_date'])
        now = datetime.utcnow()
        
        # This Week vs Last Week
        this_week = sales_df[sales_df['sale_date'] >= (now - timedelta(days=7))]
        last_week = sales_df[(sales_df['sale_date'] < (now - timedelta(days=7))) & 
                             (sales_df['sale_date'] >= (now - timedelta(days=14)))]
        
        if this_week.empty or last_week.empty:
            return {"error": "Comparison data (last 2 weeks) not sufficient."}

        # Calculate item performance
        this_week_perf = this_week.groupby('item')['quantity'].sum().reset_index()
        last_week_perf = last_week.groupby('item')['quantity'].sum().reset_index()
        
        comparison = pd.merge(this_week_perf, last_week_perf, on='item', how='outer', suffixes=('_this_week', '_last_week')).fillna(0)
        
        # Momentum Percentage
        comparison['momentum'] = ((comparison['quantity_this_week'] - comparison['quantity_last_week']) / 
                                  (comparison['quantity_last_week'] + 0.1)) * 100
        
        # Filter for Insights
        rising_stars = comparison[comparison['momentum'] > 20].sort_values(by='momentum', ascending=False)
        slowing_down = comparison[comparison['momentum'] < -20].sort_values(by='momentum', ascending=True)
        
        insights = []
        for _, row in rising_stars.head(3).iterrows():
            insights.append({
                "type": "RISING_STAR",
                "item": row['item'],
                "momentum": round(row['momentum'], 1),
                "rec": f"📈 {row['item']} is trending (+{round(row['momentum'], 1)}%). Promote it on the main menu!"
            })
            
        for _, row in slowing_down.head(3).iterrows():
            insights.append({
                "type": "SLOWING_DOWN",
                "item": row['item'],
                "momentum": round(row['momentum'], 1),
                "rec": f"📉 {row['item']} sales are dipping ({round(row['momentum'], 1)}%). Consider a temporary 'Buy 1 Get 1' deal."
            })
            
        return {
            "insights": insights,
            "comparison_data": comparison.to_dict('records')
        }

# Global singleton
forecasting_engine = ForecastingEngine()
