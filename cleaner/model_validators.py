# cleaner/model_validators.py

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Add service models to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "services" / "product" / "src"))
sys.path.append(str(project_root / "services" / "order" / "src"))

try:
    from order.models import OrderItem
    from product.models import ProductItem
except ImportError as e:
    logging.warning(f"Could not import service models: {e}")
    ProductItem = None
    OrderItem = None

logger = logging.getLogger(__name__)


class ModelValidator:
    """Validates cleaned data against service Pydantic models"""

    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.validation_errors = []
        self.fixed_rows = 0

    def validate_dataframe(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Validate and optionally fix DataFrame against appropriate model"""
        if self.dataset_name == "products" and ProductItem:
            return self._validate_products(df)
        elif self.dataset_name == "orders" and OrderItem:
            return self._validate_orders(df)
        else:
            logger.warning(f"No validation available for dataset: {self.dataset_name}")
            return df, {"skipped": True, "reason": "No model available"}

    def _validate_products(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Validate product data against ProductItem model"""
        logger.info(f"Validating {len(df)} products against ProductItem model...")

        validation_errors = []
        fixed_count = 0
        df_fixed = df.copy()

        # Test each row
        for idx in range(min(100, len(df))):  # Test first 100 rows
            row = df.iloc[idx]
            try:
                # Try to create ProductItem with minimal required fields
                price_val = row.get("price")
                rating_val = row.get("average_rating")

                ProductItem(
                    parent_asin=row.get("parent_asin", "UNKNOWN"),
                    title=row.get("title_raw", "Unknown Product"),
                    price=float(price_val) if pd.notna(price_val) else None,
                    average_rating=float(rating_val) if pd.notna(rating_val) else None,
                    rating_number=int(row.get("rating_number", 0)),
                    store=row.get("store", "Unknown Store"),
                    main_category=row.get("main_category"),
                    categories=row.get("categories_raw", []),
                    similarity=0.0,  # Test value
                    description=row.get("description_raw", []),
                    details=row.get("details_raw", {}),
                )

            except Exception as e:
                error_info = {
                    "row_index": idx,
                    "parent_asin": row.get("parent_asin", "UNKNOWN"),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                validation_errors.append(error_info)

                # Try to fix common issues
                if "price" in str(e).lower():
                    df_fixed.at[idx, "price"] = None  # Preserve null for missing prices
                    fixed_count += 1
                elif "rating" in str(e).lower():
                    df_fixed.at[idx, "average_rating"] = (
                        None  # Preserve null for missing ratings
                    )
                    df_fixed.at[idx, "rating_number"] = 0  # 0 reviews makes sense
                    fixed_count += 1
                elif "categories" in str(e).lower():
                    df_fixed.at[idx, "categories_raw"] = []
                    fixed_count += 1
                elif "details" in str(e).lower():
                    df_fixed.at[idx, "details_raw"] = {}
                    fixed_count += 1

        report = {
            "dataset": "products",
            "total_tested": min(100, len(df)),
            "validation_errors": len(validation_errors),
            "fixed_rows": fixed_count,
            "error_summary": {},
            "sample_errors": validation_errors[:5],  # First 5 errors
        }

        if validation_errors:
            # Group errors by type
            error_types = {}
            for error in validation_errors:
                error_type = error["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1
            report["error_summary"] = error_types

            logger.warning(
                f"Found {len(validation_errors)} validation errors in products"
            )
        else:
            logger.info("✅ All tested product rows passed validation!")

        return df_fixed, report

    def _validate_orders(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Validate order data against OrderItem model"""
        logger.info(f"Validating {len(df)} orders against OrderItem model...")

        validation_errors = []
        fixed_count = 0
        df_fixed = df.copy()

        # Test each row
        for idx in range(min(100, len(df))):  # Test first 100 rows
            row = df.iloc[idx]
            try:
                # Try to create OrderItem
                OrderItem(
                    order_id=str(row.get("order_id", f"ORDER_{idx}")),
                    customer_id=int(row.get("customer_id", 0)),
                    product_category=str(row.get("product_category", "Unknown")),
                    sales=float(row.get("sales", 0.0)),
                    profit=float(row.get("profit", 0.0)),
                    shipping_cost=float(row.get("shipping_cost", 0.0)),
                    order_priority=str(row.get("order_priority", "Medium")),
                    gender=row.get("gender"),
                    payment_method=row.get("payment_method"),
                    order_date=row.get("order_date"),
                    time=row.get("time"),
                    aging=row.get("aging"),
                    device_type=row.get("device_type"),
                    customer_login_type=row.get("customer_login_type"),
                    product=row.get("product"),
                    quantity=row.get("quantity"),
                    discount=row.get("discount"),
                    order_timestamp=row.get("order_timestamp"),
                    embed_text=row.get("embed_text"),
                    embed_checksum=row.get("embed_checksum"),
                )

            except Exception as e:
                error_info = {
                    "row_index": idx,
                    "order_id": row.get("order_id", "UNKNOWN"),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                validation_errors.append(error_info)

                # Try to fix common issues
                if "customer_id" in str(e).lower():
                    df_fixed.at[idx, "customer_id"] = 0
                    fixed_count += 1
                elif any(
                    field in str(e).lower()
                    for field in ["sales", "profit", "shipping_cost"]
                ):
                    for field in ["sales", "profit", "shipping_cost"]:
                        if pd.isna(row.get(field)):
                            df_fixed.at[idx, field] = 0.0
                    fixed_count += 1

        report = {
            "dataset": "orders",
            "total_tested": min(100, len(df)),
            "validation_errors": len(validation_errors),
            "fixed_rows": fixed_count,
            "error_summary": {},
            "sample_errors": validation_errors[:5],
        }

        if validation_errors:
            # Group errors by type
            error_types = {}
            for error in validation_errors:
                error_type = error["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1
            report["error_summary"] = error_types

            logger.warning(
                f"Found {len(validation_errors)} validation errors in orders"
            )
        else:
            logger.info("✅ All tested order rows passed validation!")

        return df_fixed, report
