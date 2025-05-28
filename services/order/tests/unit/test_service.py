import pytest

from order.data_service import OrderDataService


@pytest.mark.unit
def test_service_initialization(order_service: OrderDataService):
    """Test service initialization and data loading."""
    # Verify data is loaded
    assert len(order_service.df) > 0, "DataFrame should not be empty"

    # Verify column normalization
    expected_columns = {
        "order_date",
        "customer_id",
        "product_category",
        "sales",
        "profit",
        "shipping_cost",
        "order_priority",
    }
    assert all(col in order_service.df.columns for col in expected_columns), (
        "Missing expected columns"
    )

    # Allow for RangeIndex in test DataFrames
    if order_service.df.index.name is not None:
        assert order_service.df.index.name == "customer_id", (
            "DataFrame should be indexed by customer_id"
        )

    # Verify no null values in key columns
    key_columns = [
        "product_category",
        "sales",
        "profit",
        "shipping_cost",
        "order_priority",
    ]
    for col in key_columns:
        assert not order_service.df[col].isna().any(), f"Found null values in {col}"
