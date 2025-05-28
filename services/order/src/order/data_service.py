"""
Order data service implementation - CLEANED VERSION

This module provides the OrderDataService class which handles all order-related
data operations, including loading, querying, and aggregating order data.
"""

import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from libs.ecom_shared.logging import get_logger

from .models import (
    CategorySalesStats,
    CustomerStats,
    GenderProfitStats,
    OrderItem,
    ShippingCostSummary,
)

logger = get_logger(__name__)


class OrderDataService:
    """
    Service for handling order data operations.
    Loads data from CSV and provides methods for querying and aggregating.
    """

    def __init__(self, csv_path: str):
        """
        Initialize the service with data from CSV.

        Args:
            csv_path: Path to the orders CSV file
        """
        logger.info(f"Initializing OrderDataService with data from {csv_path}")
        df = pd.read_csv(csv_path)

        # Convert date columns to datetime
        if "order_date" in df.columns:
            df["order_date"] = pd.to_datetime(df["order_date"])

        self.df = df
        logger.info(f"Loaded {len(self.df)} orders")

    def _prepare_row_data(self, row: pd.Series) -> Dict[str, Any]:
        """
        Convert a DataFrame row to a dict with proper type conversions.

        Args:
            row: pandas Series representing one row

        Returns:
            Dict with cleaned data ready for Pydantic validation
        """
        data = row.to_dict()

        # Convert pandas types to basic Python types for JSON serialization
        for key, value in data.items():
            if pd.isna(value):
                data[key] = None
            elif isinstance(value, pd.Timestamp):
                data[key] = value.isoformat()
            elif isinstance(value, datetime.datetime):
                data[key] = value.isoformat()
            elif isinstance(value, pd.Timedelta):
                data[key] = str(value)
            elif hasattr(value, "item"):  # numpy/pandas scalar
                data[key] = value.item()
            elif isinstance(value, (np.integer, np.floating)):
                data[key] = value.item()

        return data

    def _df_to_order_items(
        self, df: pd.DataFrame, limit: Optional[int] = None
    ) -> List[OrderItem]:
        """
        Convert DataFrame rows to OrderItem models.

        Args:
            df: DataFrame containing order data
            limit: Optional limit on number of items to convert

        Returns:
            List of OrderItem models
        """
        if limit:
            df = df.head(limit)

        items = []
        for idx, row in df.iterrows():
            try:
                data = self._prepare_row_data(row)
                items.append(OrderItem.model_validate(data))
            except Exception as e:
                logger.warning(f"Skipping invalid row {idx}: {e}")
                continue

        return items

    def _apply_filters(
        self, df: pd.DataFrame, filters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Apply filters to a DataFrame.

        Args:
            df: DataFrame to filter
            filters: Dictionary of field-value pairs to filter by

        Returns:
            Filtered DataFrame (may be empty if no matches)
        """
        if not filters:
            logger.debug("No filters provided, returning original DataFrame")
            return df

        filtered_df = df.copy()
        initial_count = len(filtered_df)

        for field, condition in filters.items():
            pre_filter_count = len(filtered_df)

            if field not in filtered_df.columns:
                logger.warning(
                    f"Filter field '{field}' not found in DataFrame columns. Available columns: {list(filtered_df.columns)}"
                )
                # Return empty DataFrame for invalid field to prevent silent failures
                return filtered_df.iloc[0:0]

            if isinstance(condition, dict):
                # Handle operators
                if "$lt" in condition:
                    try:
                        filtered_df = filtered_df[filtered_df[field] < condition["$lt"]]
                        logger.debug(
                            f"Applied $lt filter on {field}: {pre_filter_count} -> {len(filtered_df)} rows"
                        )
                    except Exception as e:
                        logger.error(f"Error applying $lt filter on {field}: {e}")
                        return filtered_df.iloc[0:0]

                elif "$gt" in condition:
                    try:
                        filtered_df = filtered_df[filtered_df[field] > condition["$gt"]]
                        logger.debug(
                            f"Applied $gt filter on {field}: {pre_filter_count} -> {len(filtered_df)} rows"
                        )
                    except Exception as e:
                        logger.error(f"Error applying $gt filter on {field}: {e}")
                        return filtered_df.iloc[0:0]

                elif "$contains" in condition:
                    # Always convert to string for contains operations
                    try:
                        search_term = str(condition["$contains"])
                        # Convert column to string and apply contains
                        mask = (
                            filtered_df[field]
                            .astype(str)
                            .str.contains(
                                search_term,
                                case=False,
                                na=False,  # Don't match NaN values
                                regex=False,  # Treat as literal string, not regex
                            )
                        )
                        filtered_df = filtered_df[mask]
                        logger.debug(
                            f"Applied $contains filter on {field} for '{search_term}': {pre_filter_count} -> {len(filtered_df)} rows"
                        )
                    except Exception as e:
                        logger.error(f"Error applying $contains filter on {field}: {e}")
                        return filtered_df.iloc[0:0]
                else:
                    logger.warning(
                        f"Unknown operator in condition for {field}: {condition}"
                    )
                    return filtered_df.iloc[0:0]
            else:
                # Exact match
                try:
                    filtered_df = filtered_df[filtered_df[field] == condition]
                    logger.debug(
                        f"Applied exact match filter on {field}: {pre_filter_count} -> {len(filtered_df)} rows"
                    )
                except Exception as e:
                    logger.error(f"Error applying exact match filter on {field}: {e}")
                    return filtered_df.iloc[0:0]

        logger.info(f"Filtering complete: {initial_count} -> {len(filtered_df)} rows")
        return filtered_df

    def get_health_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the loaded data."""
        stats = {
            "total_orders": len(self.df),
            "categories": [],
            "date_range": {},
        }

        if "product_category" in self.df.columns:
            stats["categories"] = self.df["product_category"].unique().tolist()

        if "order_date" in self.df.columns and not self.df["order_date"].empty:
            try:
                stats["date_range"] = {
                    "start": self.df["order_date"].min().isoformat(),
                    "end": self.df["order_date"].max().isoformat(),
                }
            except:
                stats["date_range"] = {"start": None, "end": None}

        return stats

    def get_all_orders(self, limit: int = 100, offset: int = 0) -> List[OrderItem]:
        """
        Get all orders with pagination support.

        Args:
            limit: Maximum number of orders to return
            offset: Number of orders to skip

        Returns:
            List of OrderItem models
        """
        # Apply pagination
        paginated_df = self.df.iloc[offset : offset + limit]
        return self._df_to_order_items(paginated_df)

    def get_customer_stats(self, customer_id: int) -> CustomerStats:
        """
        Get comprehensive statistics for a customer.

        Args:
            customer_id: Customer ID to get stats for

        Returns:
            CustomerStats model with all customer metrics
        """
        customer_orders = self.df[self.df["customer_id"] == customer_id]

        if customer_orders.empty:
            # raise ValueError(f"No orders found for customer {customer_id}")
            return CustomerStats(
                customer_id=customer_id,
                total_orders=0,
                total_spent=0.0,
                total_profit=0.0,
                average_order_value=0.0,
                order_priorities={},
                favorite_category=None,
                preferred_device=None,
                first_order_date=None,
                last_order_date=None,
            )
        stats_dict = {
            "customer_id": int(customer_id),
            "total_orders": len(customer_orders),
            "total_spent": float(customer_orders["sales"].sum()),
            "total_profit": float(customer_orders["profit"].sum()),
            "average_order_value": float(customer_orders["sales"].mean()),
            "favorite_category": None,
            "preferred_device": None,
            "order_priorities": {},
            "first_order_date": None,
            "last_order_date": None,
        }

        if "product_category" in customer_orders.columns:
            mode_result = customer_orders["product_category"].mode()
            if not mode_result.empty:
                stats_dict["favorite_category"] = mode_result.iloc[0]

        if "device_type" in customer_orders.columns:
            mode_result = customer_orders["device_type"].mode()
            if not mode_result.empty:
                stats_dict["preferred_device"] = mode_result.iloc[0]

        if "order_priority" in customer_orders.columns:
            stats_dict["order_priorities"] = (
                customer_orders["order_priority"].value_counts().to_dict()
            )

        if "order_date" in customer_orders.columns:
            try:
                stats_dict["first_order_date"] = (
                    customer_orders["order_date"].min().isoformat()
                )
                stats_dict["last_order_date"] = (
                    customer_orders["order_date"].max().isoformat()
                )
            except:
                pass

        return CustomerStats.model_validate(stats_dict)

    def get_order_details(self, order_id: str) -> OrderItem:
        """
        Get detailed information about a specific order.

        Args:
            order_id: Order ID to retrieve

        Returns:
            OrderItem model for the specified order
        """
        order = self.df[self.df["order_id"] == order_id]

        if order.empty:
            raise ValueError(f"Order {order_id} not found")

        data = self._prepare_row_data(order.iloc[0])
        return OrderItem.model_validate(data)

    def get_orders_by_customer(self, customer_id: int, limit: int = 10):
        customer_orders = self.df[self.df["customer_id"] == customer_id]
        if customer_orders.empty:
            return []  # LLM-friendly response
        return self._df_to_order_items(customer_orders, limit)

    def get_orders_by_category(self, category: str, limit: int = 10) -> List[OrderItem]:
        """Get orders in a specific product category."""
        # Use exact match for categories
        filtered = self.df[self.df["product_category"] == category]

        if filtered.empty:
            logger.info(f"No orders found in category '{category}'")
            # Try case-insensitive match as fallback
            filtered = self.df[
                self.df["product_category"].str.lower() == category.lower()
            ]

        if filtered.empty:
            logger.info(
                f"No orders found for category '{category}' (even with case-insensitive match)"
            )
            return []  # Return empty list for consistency

        return self._df_to_order_items(filtered, limit)

    def get_recent_orders(self, limit: int = 5) -> List[OrderItem]:
        """Get the most recent orders."""
        if "order_date" not in self.df.columns:
            logger.warning("No order_date column found, returning first N orders")
            sorted_df = self.df
        else:
            sorted_df = self.df.sort_values("order_date", ascending=False)
        return self._df_to_order_items(sorted_df, limit)

    def search_orders(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
        limit: int = 10,
    ) -> List[OrderItem]:
        """
        Search orders with filters and sorting.

        Args:
            filters: Dictionary of field-value pairs to filter by
            sort: Field to sort by
            limit: Maximum number of results to return

        Returns:
            List of OrderItem models matching the search criteria
        """
        filtered_df = self._apply_filters(self.df, filters)

        # If no results after filtering, return empty list
        if filtered_df.empty:
            logger.info("No orders match the search criteria")
            return []

        if sort and sort in filtered_df.columns:
            try:
                filtered_df = filtered_df.sort_values(by=sort, ascending=False)
                logger.debug(f"Sorted by {sort} (descending)")
            except Exception as e:
                logger.warning(f"Could not sort by {sort}: {e}")

        return self._df_to_order_items(filtered_df, limit)

    def high_profit_products(
        self, min_profit: float = 100.0, limit: int = 10
    ) -> List[OrderItem]:
        """Get orders with profit above the specified threshold."""
        filters = {"profit": {"$gt": min_profit}}
        filtered = self._apply_filters(self.df, filters)

        if filtered.empty:
            logger.info(f"No orders found with profit > {min_profit}")
            return []  # Return empty list for consistency

        return self._df_to_order_items(
            filtered.sort_values("profit", ascending=False), limit
        )

    def total_sales_by_category(self) -> List[CategorySalesStats]:
        """Calculate total sales for each product category."""
        if "product_category" not in self.df.columns or "sales" not in self.df.columns:
            logger.warning("Required columns not found for category sales calculation")
            return []

        summary = (
            self.df.groupby("product_category")["sales"]
            .agg(["sum", "count"])
            .reset_index()
        )

        results = []
        for _, row in summary.iterrows():
            try:
                results.append(
                    CategorySalesStats(
                        category=row["product_category"],
                        total_sales=float(row["sum"]),
                        order_count=int(row["count"]),
                    )
                )
            except Exception as e:
                logger.warning(
                    f"Error processing category stats for {row['product_category']}: {e}"
                )
                continue

        return results

    def shipping_cost_summary(self) -> ShippingCostSummary:
        """Get summary statistics for shipping costs."""
        if "shipping_cost" not in self.df.columns:
            logger.warning("shipping_cost column not found")
            return ShippingCostSummary(
                average_cost=0.0, min_cost=0.0, max_cost=0.0, total_cost=0.0
            )

        # Filter out any NaN values
        shipping_costs = self.df["shipping_cost"].dropna()

        if shipping_costs.empty:
            return ShippingCostSummary(
                average_cost=0.0, min_cost=0.0, max_cost=0.0, total_cost=0.0
            )

        return ShippingCostSummary(
            average_cost=float(shipping_costs.mean()),
            min_cost=float(shipping_costs.min()),
            max_cost=float(shipping_costs.max()),
            total_cost=float(shipping_costs.sum()),
        )

    def profit_by_gender(self) -> List[GenderProfitStats]:
        """Calculate total profit grouped by customer gender."""
        if "gender" not in self.df.columns or "profit" not in self.df.columns:
            logger.warning("Required columns not found for gender profit calculation")
            return []

        # Group by gender and aggregate
        summary = (
            self.df.groupby("gender")
            .agg({"profit": "sum", "order_id": "count"})  # Use order_id for count
            .reset_index()
        )

        results = []
        for _, row in summary.iterrows():
            try:
                gender_display = (
                    "Male"
                    if row["gender"] == "M"
                    else "Female"
                    if row["gender"] == "F"
                    else (row["gender"] or "Unknown")
                )
                results.append(
                    GenderProfitStats(
                        gender=gender_display,
                        total_profit=float(row["profit"]),
                        order_count=int(row["order_id"]),
                    )
                )
            except Exception as e:
                logger.warning(
                    f"Error processing gender stats for {row['gender']}: {e}"
                )
                continue

        return results
