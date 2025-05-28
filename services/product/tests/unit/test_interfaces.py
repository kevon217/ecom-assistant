# services/product/tests/unit/test_interfaces.py
"""
Test ProductStoreInterface contract compliance.
Ensures all store implementations follow the interface correctly.
"""

from abc import ABC
from typing import List, Optional

import pytest

from product.interfaces import ProductStoreInterface
from product.models import DocumentFilters, ProductItem, ProductItemLLM, SearchFilters


@pytest.mark.unit
class TestProductStoreInterface:
    """Test that ProductStoreInterface is properly defined."""

    def test_interface_is_abstract(self):
        """Test that ProductStoreInterface is abstract and cannot be instantiated."""
        assert issubclass(ProductStoreInterface, ABC)

        with pytest.raises(TypeError):
            ProductStoreInterface()

    def test_interface_has_required_methods(self):
        """Test that interface defines all required abstract methods."""
        expected_methods = [
            "semantic_search",
            # "lexical_search",
            # "hybrid_search",
            # "get_by_ids",  # Commented out in interface
            "count",
            "health_check",
            "get_metadata_values",
        ]

        # Get all abstract methods from the interface
        abstract_methods = set()
        for method_name in dir(ProductStoreInterface):
            method = getattr(ProductStoreInterface, method_name)
            if hasattr(method, "__isabstractmethod__") and method.__isabstractmethod__:
                abstract_methods.add(method_name)

        for method_name in expected_methods:
            assert method_name in abstract_methods, (
                f"Method {method_name} should be abstract"
            )

    def test_interface_method_signatures(self):
        """Test that interface methods have correct signatures."""
        # Check semantic_search signature
        semantic_search = getattr(ProductStoreInterface, "semantic_search")
        assert semantic_search is not None

        # Check that methods exist (signature validation would require inspection)
        required_methods = [
            "semantic_search",
            # "lexical_search",
            # "hybrid_search",
            # "get_by_ids",  # Commented out in interface
            "count",
            "health_check",
            "get_metadata_values",
        ]

        for method_name in required_methods:
            assert hasattr(ProductStoreInterface, method_name)


@pytest.mark.unit
class MockProductStore(ProductStoreInterface):
    """Mock implementation for testing interface compliance."""

    def __init__(self):
        self.products = [
            ProductItem(
                parent_asin="B001",
                title="Test Product 1",
                title_raw="test product 1",
                price=99.99,
                average_rating=4.5,
                rating_number=100,
                store="TestStore",
                main_category="Electronics",
                categories=["Electronics", "Gadgets"],
                similarity=0.9,
                confidence="high",
                search_type="semantic",
            )
        ]

    def semantic_search(
        self,
        query: str,
        limit: int,
        filters: Optional[SearchFilters] = None,
        document_filters: Optional[DocumentFilters] = None,
    ) -> List[ProductItem]:
        return self.products[:limit]

    # def lexical_search(
    #     self, query: str, limit: int, filters: Optional[SearchFilters] = None
    # ) -> List[ProductItem]:
    #     return self.products[:limit]

    # def hybrid_search(
    #     self,
    #     query: str,
    #     limit: int,
    #     filters: Optional[SearchFilters] = None,
    #     semantic_weight: float = 0.7,
    #     lexical_weight: float = 0.3,
    # ) -> List[ProductItem]:
    #     return self.products[:limit]

    # def get_by_ids(self, ids: List[str]) -> List[ProductItem]:
    #     return [p for p in self.products if p.parent_asin in ids]

    def count(self) -> int:
        return len(self.products)

    def health_check(self) -> bool:
        return True

    def get_metadata_values(self, field: str) -> List[tuple]:
        if field == "store":
            return [("TestStore", 100)]
        elif field == "main_category":
            return [("Electronics", 100)]
        return []


@pytest.mark.unit
class TestMockProductStore:
    """Test that mock implementation satisfies interface."""

    def test_mock_implements_interface(self):
        """Test that MockProductStore implements ProductStoreInterface."""
        mock_store = MockProductStore()
        assert isinstance(mock_store, ProductStoreInterface)

    def test_mock_semantic_search(self):
        """Test mock semantic search."""
        mock_store = MockProductStore()
        results = mock_store.semantic_search("test", 1)
        assert len(results) == 1
        assert isinstance(results[0], ProductItem)

    def test_mock_health_check(self):
        """Test mock health check."""
        mock_store = MockProductStore()
        assert mock_store.health_check() is True

    def test_mock_count(self):
        """Test mock count."""
        mock_store = MockProductStore()
        assert mock_store.count() == 1

    def test_mock_get_metadata_values(self):
        """Test mock metadata retrieval."""
        mock_store = MockProductStore()
        store_tuples = mock_store.get_metadata_values("store")
        assert isinstance(store_tuples, list)
        assert len(store_tuples) > 0

        # Should be tuples of (value, count)
        first_tuple = store_tuples[0]
        assert isinstance(first_tuple, tuple)
        assert len(first_tuple) == 2

        # Check the value exists
        store_values = [t[0] for t in store_tuples]
        assert "TestStore" in store_values
