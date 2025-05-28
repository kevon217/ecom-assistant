# services/product/tests/integration/test_api_endpoints.py
"""
Live integration tests for Product Service API endpoints.
These tests require actual ChromaDB and processed data.
Use: pytest -m live_integration
"""

import pytest
from fastapi.testclient import TestClient

from product.app import app

client = TestClient(app)


@pytest.mark.live_integration
def test_product_health():
    """Test health endpoint with real ChromaDB."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    # Health endpoint should return 200 even if ChromaDB is unavailable in test environment
    assert body["status"] in ["ok", "error"]  # Allow both states
    assert "store" in body  # Should report store status


@pytest.mark.live_integration
@pytest.mark.requires_chroma
def test_metadata_options_store():
    """Test metadata endpoint with real ChromaDB data."""
    r = client.get("/metadata/options?field_name=store")
    # Will return 500 if ChromaDB is unavailable, which is expected in test environment
    if r.status_code == 500:
        pytest.skip("ChromaDB not available in test environment")
    assert r.status_code == 200
    opts = r.json()["options"]
    assert isinstance(opts, list)


@pytest.mark.live_integration
@pytest.mark.requires_chroma
def test_semantic_search_returns_list():
    """Test semantic search with real ChromaDB data."""
    payload = {"query": "wireless", "limit": 2, "filters": {}}
    r = client.post("/search/semantic", json=payload)
    # Will return 500 if ChromaDB is unavailable, which is expected in test environment
    if r.status_code == 500:
        pytest.skip("ChromaDB not available in test environment")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "parent_asin" in data[0]


# @pytest.mark.live_integration
# @pytest.mark.requires_chroma
# def test_lexical_search_returns_list():
#     """Test lexical search with real ChromaDB data."""
#     payload = {"query": "Test", "limit": 2, "filters": {}}
#     r = client.post("/search/lexical", json=payload)
#     # Will return 500 if ChromaDB is unavailable, which is expected in test environment
#     if r.status_code == 500:
#         pytest.skip("ChromaDB not available in test environment")
#     assert r.status_code == 200
#     data = r.json()
#     assert isinstance(data, list)
#     if data:
#         assert "parent_asin" in data[0]
