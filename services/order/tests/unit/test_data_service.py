# services/order/tests/unit/test_data_service.py

from unittest.mock import Mock

import pandas as pd
import pytest

from order.data_service import OrderDataService
from order.models import CategorySalesStats, OrderItem


@pytest.mark.unit
def test_apply_filters_exact_match(order_service):
    df = order_service.df
    # Ensure required fields are present
    if "order_priority" not in df.columns:
        df["order_priority"] = "Medium"
    filtered = order_service._apply_filters(df, {"product_category": "Books"})
    assert all(row == "Books" for row in filtered["product_category"])


@pytest.mark.unit
def test_get_recent_orders(order_service):
    # Create a DataFrame with all required fields
    df = pd.DataFrame(
        [
            {
                "order_id": "1",
                "customer_id": 42,
                "order_priority": "High",
                "order_date": "2024-01-01",
                "product_category": "Books",
                "sales": 10.0,
                "profit": 2.0,
                "shipping_cost": 1.0,
                "gender": "M",
                "payment_method": "Card",
                "time": "14:30:00",
                "aging": 2.0,
                "order_timestamp": "2024-01-01 14:30:00",
            },
            {
                "order_id": "2",
                "customer_id": 43,
                "order_priority": "Medium",
                "order_date": "2024-01-02",
                "product_category": "Electronics",
                "sales": 20.0,
                "profit": 5.0,
                "shipping_cost": 2.0,
                "gender": "F",
                "payment_method": "PayPal",
                "time": "15:45:00",
                "aging": 1.0,
                "order_timestamp": "2024-01-02 15:45:00",
            },
        ]
    )
    # Convert order_date to datetime
    df["order_date"] = pd.to_datetime(df["order_date"])

    service = OrderDataService.__new__(OrderDataService)
    service.df = df
    recent = service.get_recent_orders(limit=2)
    assert len(recent) == 2
    assert all(isinstance(order, OrderItem) for order in recent)
    assert all(hasattr(order, "customer_id") for order in recent)
    assert all(hasattr(order, "order_priority") for order in recent)


@pytest.mark.unit
def test_get_orders_by_customer(order_service):
    # Create a DataFrame with all required fields
    df = pd.DataFrame(
        [
            {
                "order_id": "1",
                "customer_id": 42,
                "order_priority": "High",
                "order_date": "2024-01-01",
                "product_category": "Books",
                "sales": 10.0,
                "profit": 2.0,
                "shipping_cost": 1.0,
                "gender": "M",
                "payment_method": "Card",
                "time": "14:30:00",
                "aging": 2.0,
                "order_timestamp": "2024-01-01 14:30:00",
            },
            {
                "order_id": "2",
                "customer_id": 42,
                "order_priority": "Medium",
                "order_date": "2024-01-02",
                "product_category": "Electronics",
                "sales": 20.0,
                "profit": 5.0,
                "shipping_cost": 2.0,
                "gender": "F",
                "payment_method": "PayPal",
                "time": "15:45:00",
                "aging": 1.0,
                "order_timestamp": "2024-01-02 15:45:00",
            },
        ]
    )
    service = OrderDataService.__new__(OrderDataService)
    service.df = df
    orders = service.get_orders_by_customer(customer_id=42, limit=5)
    assert all(isinstance(order, OrderItem) for order in orders)
    assert all(order.customer_id == 42 for order in orders)

    # Test non-existent customer - NOW RETURNS EMPTY LIST, NOT ERROR
    orders = service.get_orders_by_customer(customer_id=-1, limit=1)
    assert orders == []  # Should return empty list
    assert len(orders) == 0


@pytest.mark.unit
def test_total_sales_by_category(order_service):
    # Now returns list of CategorySalesStats objects
    summary = order_service.total_sales_by_category()

    # Check that we get CategorySalesStats objects
    assert all(isinstance(s, CategorySalesStats) for s in summary)

    # Check categories
    categories = {s.category for s in summary}
    assert "Books" in categories and "Electronics" in categories

    # Check types and values
    for s in summary:
        assert isinstance(s.total_sales, float)
        assert isinstance(s.order_count, int)
        assert s.total_sales >= 0
        assert s.order_count >= 0
