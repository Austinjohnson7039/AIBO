import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.stock_engine import stock_engine

class ForecastingEngine:
    def __init__(self):
        pass

    def get_inventory_forecast(self, db: Session, tenant_id: int, lookback_days=30, forecast_days=7, safety_buffer=0.15):
        """
        Calculates ingredient burn rates and predicts future needs for a specific tenant.
        Ensures 100% data isolation by loading tenant-specific DataFrames.
        """
        grocery_df, recipes_df, sales_df, inv_df = stock_engine.load_data(db, tenant_id)
        
        if sales_df.empty:
            return {
                "shopping_list": [],
                "runway_metrics": [],
                "error": "No sales data found for forecasting."
            }

        # 1. Calculate Daily Consumption for each ingredient
        sales_df['sale_date'] = pd.to_datetime(sales_df['sale_date'])
        
        # Fallback Logic: If no sales in last 30 days, use full history for the demo
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        recent_sales = sales_df[sales_df['sale_date'] >= cutoff]
        
        if recent_sales.empty:
            recent_sales = sales_df  # Use full history if recent is empty
            # BUG FIX (BUG 13): effective_days was 0 when all sales are on same day,
            # causing ZeroDivisionError in burn rate. Floor to minimum 1.
            effective_days = max(1, (sales_df['sale_date'].max() - sales_df['sale_date'].min()).days + 1)
        else:
            effective_days = max(1, lookback_days)  # Also floor lookback to prevent edge cases

        if recipes_df.empty:
            return {"shopping_list": [], "runway_metrics": [], "error": "No recipes found."}

        # Merge sales with recipes to find ingredient usage (Left Join captures naked retail inventory)
        usage_merged = pd.merge(recent_sales, recipes_df, left_on='item', right_on='menu_item', how='left')
        if usage_merged.empty:
            return {"shopping_list": [], "runway_metrics": [], "error": "No matching recipes for sold items."}
            
        # For Retail items (No compounding recipe), Treat the sold item exactly as the naked grocery ingredient
        usage_merged['ingredient'] = usage_merged['ingredient'].fillna(usage_merged['item'])
        usage_merged['quantity_per_unit'] = usage_merged['quantity_per_unit'].fillna(1.0)

        usage_merged['total_used'] = usage_merged['quantity'] * usage_merged['quantity_per_unit']
        
        # Aggregate usage by ingredient
        usage_agg = usage_merged.groupby('ingredient')['total_used'].sum().reset_index()
        
        # Calculate daily burn rate
        usage_agg['daily_burn_rate'] = usage_agg['total_used'] / effective_days
        
        # 2. Join with Grocery Stock to calculate "Runway"
        forecast_df = pd.merge(grocery_df, usage_agg, left_on='ingredient_name', right_on='ingredient', how='left')
        forecast_df['daily_burn_rate'] = forecast_df['daily_burn_rate'].fillna(0)
        
        # Days of stock left: current_stock / daily_burn_rate (safe divide)
        forecast_df['runway_days'] = forecast_df.apply(
            lambda x: x['current_stock'] / x['daily_burn_rate'] if x['daily_burn_rate'] > 0 else 999, axis=1
        )
        
        # 3. Smart Shopping List
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

    def get_marketing_insights(self, db: Session, tenant_id: int):
        """
        Analyzes sales momentum for a specific tenant to suggest promotions.
        """
        _, _, sales_df, _ = stock_engine.load_data(db, tenant_id)
        
        if sales_df.empty:
            return {"insights": [], "error": "No sales data found."}

        sales_df['sale_date'] = pd.to_datetime(sales_df['sale_date'])
        
        # For historical demo data, we shift 'now' to the last sale date to show momentum
        reference_date = sales_df['sale_date'].max()
        if not reference_date: reference_date = datetime.utcnow()
        
        # This Week vs Last Week (Relative to data availability)
        this_week = sales_df[sales_df['sale_date'] >= (reference_date - timedelta(days=7))]
        last_week = sales_df[(sales_df['sale_date'] < (reference_date - timedelta(days=7))) & 
                             (sales_df['sale_date'] >= (reference_date - timedelta(days=14)))]
        
        if this_week.empty:
            return {"insights": [], "error": "Insufficient recent sales for trend analysis."}

        # Calculate item performance
        this_week_perf = this_week.groupby('item')['quantity'].sum().reset_index()
        last_week_perf = last_week.groupby('item')['quantity'].sum().reset_index() if not last_week.empty else pd.DataFrame(columns=['item', 'quantity'])
        
        comparison = pd.merge(this_week_perf, last_week_perf, on='item', how='outer', suffixes=('_this_week', '_last_week')).fillna(0)
        
        # Momentum Percentage - Capped statically to prevent exploding division-by-zero artifacts
        comparison['momentum'] = np.where(
            comparison['quantity_last_week'] > 0,
            ((comparison['quantity_this_week'] - comparison['quantity_last_week']) / comparison['quantity_last_week']) * 100,
            # If last week was 0 and this week is positive, cap growth indicator to a logical maximum (e.g. 100%)
            np.where(comparison['quantity_this_week'] > 0, 100.0, 0.0)
        )
        
        rising_stars = comparison[comparison['momentum'] > 10].sort_values(by='momentum', ascending=False)
        
        insights = []
        for _, row in rising_stars.head(3).iterrows():
            insights.append({
                "type": "RISING_STAR",
                "item": row['item'],
                "momentum": round(row['momentum'], 1),
                "rec": f"📈 {row['item']} is trending ({'+' if row['momentum']>0 else ''}{round(row['momentum'], 1)}%). Promote it!"
            })
            
        return {
            "insights": insights,
            "comparison_data": comparison.to_dict('records')
        }

# Global singleton
forecasting_engine = ForecastingEngine()
