import pandas as pd
import logging

logger = logging.getLogger(__name__)

def fuzzy_map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attempts to map messy Excel columns to ['item', 'quantity', 'revenue'].
    Uses simple keyword matching / heuristics to identify standard POS export formats.
    """
    column_mapping = {}
    
    raw_cols = df.columns.tolist()
    clean_cols = [str(c).lower().strip().replace(' ', '_') for c in raw_cols]
    
    # 1. Map Date
    date_keywords = ['date', 'time', 'timestamp', 'day']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in date_keywords):
            column_mapping[raw] = 'date'
            
    # 2. Map Item
    item_keywords = ['item', 'product', 'name', 'menu', 'dish', 'beverage', 'sku', 'description']
    for raw, clean in zip(raw_cols, clean_cols):
        if any(kw in clean for kw in item_keywords) and 'item' not in column_mapping.values():
            column_mapping[raw] = 'item'
            
    # 3. Map Quantity
    qty_keywords = ['qty', 'quantity', 'count', 'sold', 'units', 'volume']
    for raw, clean in zip(raw_cols, clean_cols):
        # Prioritize exact matches like 'qty' or 'quantity' over 'amount' which could be money
        if raw not in column_mapping and any(kw in clean for kw in qty_keywords):
            column_mapping[raw] = 'quantity'
            
    # 4. Map Revenue
    rev_keywords = ['rev', 'revenue', 'price', 'total', 'sales', 'amount', 'inr', 'rs']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in rev_keywords):
            if 'revenue' not in column_mapping.values():
                column_mapping[raw] = 'revenue'
                
    missing = []
    if 'item' not in column_mapping.values(): missing.append('item (Product Name)')
    if 'quantity' not in column_mapping.values(): missing.append('quantity (Units Sold)')
    if 'revenue' not in column_mapping.values(): missing.append('revenue (Total Sales, INR)')
    
    if missing:
        raise ValueError(f"Missing required columns. We couldn't find: {', '.join(missing)}.\n\nYour headers were: {list(raw_cols)}.\nPlease download the AIBO Template and copy your sales into it to ensure perfect compatibility!")
    df = df.rename(columns=column_mapping)
    
    # Filter and clean
    cols_to_keep = ['item', 'quantity', 'revenue']
    if 'date' in df.columns:
        cols_to_keep.append('date')
        
    df = df[cols_to_keep]
    df = df.dropna(subset=['item', 'quantity'])
    
    # Ensure types
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0.0).astype(float)
    df['item'] = df['item'].astype(str)
    
    return df
