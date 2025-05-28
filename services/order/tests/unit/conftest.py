import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from order.app import app
from order.data_service import OrderDataService


@pytest.fixture
def sample_orders_csv(tmp_path):
    data = {
        "order_id": ["ORD001", "ORD002", "ORD003"],
        "customer_id": [42, 43, 42],
        "product_category": ["Books", "Electronics", "Books"],
        "sales": [12.5, 99.9, 15.0],
        "profit": [2.5, 10.0, 3.0],
        "shipping_cost": [1.0, 5.0, 1.5],
        "order_date": ["2025-01-01", "2025-02-02", "2025-03-03"],
        "order_priority": ["High", "Medium", "Low"],
        "time": ["14:30:00", "15:45:00", "16:20:00"],
        "aging": [2.0, 1.5, 3.0],
        "order_timestamp": [
            "2025-01-01 14:30:00",
            "2025-02-02 15:45:00",
            "2025-03-03 16:20:00",
        ],
        "gender": ["M", "F", "M"],
        "payment_method": ["Credit Card", "PayPal", "Debit Card"],
    }
    df = pd.DataFrame(data)
    path = tmp_path / "orders.csv"
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture(autouse=True)
def override_env(monkeypatch, sample_orders_csv):
    monkeypatch.setenv("TEST_ORDER_DATA_PATH", sample_orders_csv)


@pytest.fixture
def order_service():
    return OrderDataService(csv_path=Path(os.getenv("TEST_ORDER_DATA_PATH")))


@pytest.fixture
def client():
    return TestClient(app)
