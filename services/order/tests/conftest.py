# services/order/tests/conftest.py
"""
Minimal test configuration for order service tests.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ["TESTING"] = "true"


# Configure Python path for testing
def setup_python_path():
    """Set up Python path to allow imports from both service and shared libs."""
    # Get absolute paths
    project_root = Path(__file__).parent.parent.parent.parent.absolute()
    order_src = Path(__file__).parent.parent / "src"

    # Add paths to sys.path if not already present
    paths_to_add = [str(order_src), str(project_root)]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)


# Set up paths immediately when module is imported
setup_python_path()


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "order_id": "TEST001",
        "customer_id": 12345,
        "product_category": "Electronics",
        "sales": 99.99,
        "profit": 19.99,
        "shipping_cost": 5.99,
        "order_priority": "High",
        "gender": "M",
        "payment_method": "Credit Card",
        "order_date": "2024-01-01",
        "time": "10:30:00",
        "aging": 30.0,
        "device_type": "Desktop",
        "customer_login_type": "New",
        "product": "Test Product",
        "quantity": 2.0,
        "discount": 5.0,
        "order_timestamp": "2024-01-01T10:30:00Z",
        "embed_text": "Test order embedding text",
        "embed_checksum": "test_checksum_123",
    }


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Add any cleanup logic here if needed
    pass
