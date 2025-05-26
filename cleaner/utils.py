import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Add service models to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "services" / "product" / "src"))
sys.path.append(str(project_root / "services" / "order" / "src"))


def normalize_text(text: str) -> str:
    if not text:
        return ""
    txt = text.lower()
    txt = re.sub(r"[^\w\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def create_product_item_simple(row):
    """Simplified version with just essential error handling"""

    # Handle missing prices (your biggest issue)
    price = 0.0
    if pd.notna(row.get("price")):
        try:
            price = float(row["price"])
        except (ValueError, TypeError):
            price = 0.0

    # Handle string representations of lists/dicts
    def safe_parse_list(value):
        if pd.isna(value) or not value:
            return []
        if isinstance(value, list):
            return value
        try:
            return ast.literal_eval(str(value))
        except:
            return []

    def safe_parse_dict(value):
        if pd.isna(value) or not value:
            return {}
        if isinstance(value, dict):
            return value
        try:
            return ast.literal_eval(str(value))
        except:
            return {}

    return ProductItem(
        parent_asin=str(row["parent_asin"]),
        title=str(row["title_raw"]),
        price=price,  # ✅ Handles 25% missing prices
        average_rating=float(row.get("average_rating", 0.0)),
        rating_number=int(row.get("rating_number", 0)),
        store=str(row.get("store", "Unknown")),
        main_category=row.get("main_category"),
        categories=safe_parse_list(
            row.get("categories_raw")
        ),  # ✅ Handles string lists
        similarity=0.0,
        description=safe_parse_list(row.get("description_raw")),
        details=safe_parse_dict(row.get("details_raw")),  # ✅ Handles string dicts
    )
