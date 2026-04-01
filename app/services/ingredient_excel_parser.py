"""
ingredient_excel_parser.py
──────────────────────────
Fuzzy column mapping for ingredient/grocery Excel uploads.
Similar to the sales excel_parser but maps to ingredient fields.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def fuzzy_map_ingredient_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attempts to map messy Excel columns to standard ingredient fields:
    Required: ['ingredient_name']
    Optional: ['category', 'unit', 'current_stock', 'reorder_level', 'unit_cost_inr']
    
    Uses keyword matching to identify columns from various POS/inventory export formats.
    """
    column_mapping = {}
    raw_cols = df.columns.tolist()
    clean_cols = [str(c).lower().strip().replace(' ', '_').replace('-', '_') for c in raw_cols]

    # 1. Map Ingredient Name (required)
    name_keywords = ['ingredient', 'name', 'item', 'product', 'material', 'grocery', 'raw_material']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in name_keywords):
            if 'ingredient_name' not in column_mapping.values():
                column_mapping[raw] = 'ingredient_name'

    # 2. Map Category
    cat_keywords = ['category', 'type', 'group', 'class', 'section']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in cat_keywords):
            if 'category' not in column_mapping.values():
                column_mapping[raw] = 'category'

    # 3. Map Unit
    unit_keywords = ['unit', 'uom', 'measure', 'measurement']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in unit_keywords):
            if 'unit' not in column_mapping.values():
                column_mapping[raw] = 'unit'

    # 4. Map Current Stock
    stock_keywords = ['stock', 'quantity', 'qty', 'available', 'on_hand', 'current', 'balance']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in stock_keywords):
            if 'current_stock' not in column_mapping.values():
                column_mapping[raw] = 'current_stock'

    # 5. Map Reorder Level
    reorder_keywords = ['reorder', 'minimum', 'min_stock', 'threshold', 'safety', 'min_level', 'low']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in reorder_keywords):
            if 'reorder_level' not in column_mapping.values():
                column_mapping[raw] = 'reorder_level'

    # 6. Map Unit Cost
    cost_keywords = ['cost', 'price', 'rate', 'unit_cost', 'cost_per', 'inr', 'rs', 'amount']
    for raw, clean in zip(raw_cols, clean_cols):
        if raw not in column_mapping and any(kw in clean for kw in cost_keywords):
            if 'unit_cost_inr' not in column_mapping.values():
                column_mapping[raw] = 'unit_cost_inr'

    # Validate: ingredient_name is required
    if 'ingredient_name' not in column_mapping.values():
        raise ValueError(
            f"Could not find a column for 'Ingredient Name'.\n"
            f"Your headers were: {list(raw_cols)}.\n"
            f"Please download the AIBO Ingredient Template and copy your data into it."
        )

    # Rename and fill defaults
    df = df.rename(columns=column_mapping)

    # Ensure all expected columns exist with defaults
    if 'category' not in df.columns:
        df['category'] = 'Other'
    if 'unit' not in df.columns:
        df['unit'] = 'kg'
    if 'current_stock' not in df.columns:
        df['current_stock'] = 0.0
    if 'reorder_level' not in df.columns:
        df['reorder_level'] = 10.0
    if 'unit_cost_inr' not in df.columns:
        df['unit_cost_inr'] = 0.0

    # Select and clean
    cols_to_keep = ['ingredient_name', 'category', 'unit', 'current_stock', 'reorder_level', 'unit_cost_inr']
    df = df[cols_to_keep]
    df = df.dropna(subset=['ingredient_name'])
    df = df[df['ingredient_name'].astype(str).str.strip() != '']

    # Ensure types
    df['ingredient_name'] = df['ingredient_name'].astype(str).str.strip()
    df['category'] = df['category'].astype(str).str.strip().replace('', 'Other').replace('nan', 'Other')
    df['unit'] = df['unit'].astype(str).str.strip().replace('', 'kg').replace('nan', 'kg')
    df['current_stock'] = pd.to_numeric(df['current_stock'], errors='coerce').fillna(0.0)
    df['reorder_level'] = pd.to_numeric(df['reorder_level'], errors='coerce').fillna(10.0)
    df['unit_cost_inr'] = pd.to_numeric(df['unit_cost_inr'], errors='coerce').fillna(0.0)

    return df
