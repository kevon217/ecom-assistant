# services/order/tests/integration/conftest.py
"""
Integration test configuration for order service.
Requires running order service on port 8002.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def verify_order_service():
    """Verify order service is running before tests."""
    import requests

    try:
        response = requests.get("http://127.0.0.1:8002/health", timeout=2)
        if response.status_code != 200:
            pytest.skip("Order service not running on port 8002")
    except requests.exceptions.RequestException:
        pytest.skip(
            "Order service not available - start with: cd services/order && python -m uvicorn order.app:app --port 8002"
        )
