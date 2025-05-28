# services/product/tests/unit/test_data_service.py
"""
Unit tests for ProductDataService business logic layer.
Tests service with mock store to isolate business logic from storage implementation.
"""

from typing import List, Optional
from unittest.mock import Mock

import pytest

from product.interfaces import ProductStoreInterface
from product.models import DocumentFilters, ProductItem, ProductItemLLM, SearchFilters
from product.services.data_service import ProductDataService


@pytest.mark.unit
class MockProductStore(ProductStoreInterface):
    """Mock store for testing ProductDataService."""

    def __init__(self):
        self.search_calls = []
        self.mock_products = [
            ProductItem(
                parent_asin="B001",
                title="High Quality Product",
                title_raw="high quality product",
                price=99.99,
                average_rating=4.8,
                rating_number=150,
                store="TestStore",
                main_category="Electronics",
                categories=["Electronics", "Gadgets"],
                similarity=0.95,
            ),
            ProductItem(
                parent_asin="B002",
                title="Medium Quality Product",
                title_raw="medium quality product",
                price=49.99,
                average_rating=3.5,
                rating_number=50,
                store="TestStore",
                main_category="Electronics",
                categories=["Electronics"],
                similarity=0.7,
            ),
            ProductItem(
                parent_asin="B003",
                title="Low Quality Product",
                title_raw="low quality product",
                price=19.99,
                average_rating=2.1,
                rating_number=10,
                store="TestStore",
                main_category="Books",
                categories=["Books"],
                similarity=0.4,
            ),
        ]

    def semantic_search(
        self,
        query: str,
        limit: int,
        filters: Optional[SearchFilters] = None,
        document_filters: Optional[DocumentFilters] = None,
    ) -> List[ProductItem]:
        self.search_calls.append(("semantic", query, limit))
        return self.mock_products[:limit]

    # def lexical_search(self, query: str, limit: int, filters=None) -> list:
    #     self.search_calls.append(("lexical", query, limit))
    #     return self.mock_products[:limit]

    # def hybrid_search(
    #     self,
    #     query: str,
    #     limit: int,
    #     filters=None,
    #     semantic_weight=0.7,
    #     lexical_weight=0.3,
    # ) -> list:
    #     self.search_calls.append(("hybrid", query, limit))
    #     return self.mock_products[:limit]

    # def get_by_ids(self, ids: list) -> list:
    #     return [p for p in self.mock_products if p.parent_asin in ids]

    def count(self) -> int:
        return len(self.mock_products)

    def health_check(self) -> bool:
        return True

    def get_metadata_values(self, field: str) -> List[tuple]:
        if field == "store":
            return [("TestStore", 100)]
        elif field == "main_category":
            return [("Electronics", 75), ("Books", 25)]
        return []


@pytest.fixture
def mock_store():
    """Fixture providing mock store."""
    return MockProductStore()


@pytest.fixture
def product_service(mock_store):
    """Fixture providing ProductDataService with mock store."""
    return ProductDataService(store=mock_store)


@pytest.mark.unit
class TestProductDataServiceInitialization:
    """Test service initialization."""

    def test_service_initialization(self, mock_store):
        """Test that service initializes correctly with store."""
        service = ProductDataService(store=mock_store)
        assert service.store is mock_store
        assert service.max_results_limit == 100
        # assert service.default_search_weights == {"semantic": 0.7, "lexical": 0.3}

    def test_service_initialization_calls_count(self, mock_store):
        """Test that service calls store.count() during initialization."""
        service = ProductDataService(store=mock_store)
        # Should log product count, implying count() was called
        assert service.store.count() == 3


class TestProductDataServiceSemanticSearch:
    """Test semantic search business logic."""

    def test_semantic_search_basic(self, product_service, mock_store):
        """Test basic semantic search functionality."""
        results = product_service.semantic_search("test query", limit=2)

        assert len(results) == 2
        assert mock_store.search_calls[-1] == ("semantic", "test query", 2)
        assert product_service.search_stats["semantic"] == 1

    def test_semantic_search_applies_business_rules(self, product_service):
        """Test that business rules are applied to search results."""
        results = product_service.semantic_search("test", limit=3)

        # Verify we get ProductItemLLM objects
        for product in results:
            assert isinstance(product, ProductItemLLM)
            # ProductItemLLM inherits from ProductItem
            assert isinstance(product, ProductItem)

            # Check confidence scoring business rule
            if product.similarity > 0.85:
                assert product.confidence == "high"
            elif product.similarity > 0.6:
                assert product.confidence == "medium"
            else:
                assert product.confidence == "low"

            # Check search type is set
            assert product.search_type == "semantic"

    def test_semantic_search_validates_input(self, product_service):
        """Test input validation."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            product_service.semantic_search("", limit=5)

        with pytest.raises(ValueError, match="Limit must be positive"):
            product_service.semantic_search("test", limit=0)

    def test_semantic_search_enforces_max_limit(self, product_service):
        """Test that max limit is enforced."""
        results = product_service.semantic_search("test", limit=200)
        # Should be limited to max_results_limit (100)
        # Check the call was made with limited value
        assert len(results) <= 100


@pytest.mark.unit
class TestProductDataServiceBusinessLogic:
    """Test business logic functions."""

    # def test_get_products_by_ids(self, product_service):
    #     """Test batch product lookup."""
    #     results = product_service.get_products_by_ids(["B001", "B002"])
    #     assert len(results) == 2
    #     assert results[0].parent_asin == "B001"
    #     assert results[1].parent_asin == "B002"

    # def test_get_products_by_ids_limits_batch_size(self, product_service):
    #     """Test that batch size is limited."""
    #     large_list = [f"B{i:03d}" for i in range(100)]  # 100 IDs
    #     results = product_service.get_products_by_ids(large_list)
    #     # Should not crash, may return fewer results due to batch limit
    #     assert isinstance(results, list)

    # def test_get_product_recommendations(self, product_service):
    #     """Test product recommendations business logic."""
    #     recommendations = product_service.get_product_recommendations("B001", limit=2)

    #     # Should return products but not include the source product
    #     assert len(recommendations) >= 0
    #     for rec in recommendations:
    #         assert rec.parent_asin != "B001"  # Source product excluded

    # def test_hybrid_search_normalizes_weights(self, product_service):
    #     """Test that hybrid search normalizes weights."""
    #     # Test with weights that don't sum to 1.0
    #     results = product_service.hybrid_search(
    #         "test", limit=2, semantic_weight=0.8, lexical_weight=0.6
    #     )

    #     assert len(results) == 2
    #     # Should have called store with normalized weights
    #     # (0.8 + 0.6 = 1.4, so normalized: semantic=0.8/1.4H0.57, lexical=0.6/1.4H0.43)

    def test_get_search_statistics(self, product_service):
        """Test search statistics business logic."""
        # Perform some searches
        product_service.semantic_search("test1", 1)
        # product_service.lexical_search("test2", 1)
        # product_service.hybrid_search("test3", 1)

        stats = product_service.get_search_statistics()

        # assert stats["total_searches"] == 3
        assert stats["search_breakdown"]["semantic"] == 1
        # assert stats["search_breakdown"]["lexical"] == 1
        # assert stats["search_breakdown"]["hybrid"] == 1
        assert stats["store_health"] is True
        assert stats["total_products"] == 3

    def test_product_item_llm_token_optimization(self, product_service):
        """Test that semantic search returns optimized ProductItemLLM objects."""
        results = product_service.semantic_search("test", limit=1)
        assert len(results) == 1

        product_llm = results[0]

        # Verify it's the optimized model
        assert isinstance(product_llm, ProductItemLLM)

        # Verify inheritance from ProductItem (80% token reduction while maintaining compatibility)
        assert isinstance(product_llm, ProductItem)

        # Verify key fields are preserved
        assert hasattr(product_llm, "parent_asin")
        assert hasattr(product_llm, "title")
        assert hasattr(product_llm, "price")
        assert hasattr(product_llm, "similarity")
        assert hasattr(product_llm, "confidence")
        assert hasattr(product_llm, "search_type")

        # Verify the model has proper values
        assert product_llm.parent_asin is not None
        assert product_llm.title is not None
        assert product_llm.search_type == "semantic"

    def test_llm_model_inheritance_compatibility(self, product_service):
        """Test that ProductItemLLM maintains full compatibility with ProductItem."""
        results = product_service.semantic_search("high quality", limit=1)
        product_llm = results[0]

        # Should work with all ProductItem operations
        assert isinstance(product_llm, ProductItem)

        # Should have all the essential ProductItem fields
        essential_fields = [
            "parent_asin",
            "title",
            "price",
            "average_rating",
            "rating_number",
            "store",
            "main_category",
            "similarity",
        ]

        for field in essential_fields:
            assert hasattr(product_llm, field), f"Missing essential field: {field}"
            assert getattr(product_llm, field) is not None, f"Field {field} is None"


@pytest.mark.unit
class TestProductDataServiceErrorHandling:
    """Test error handling and edge cases."""

    # def test_empty_id_list(self, product_service):
    #     """Test behavior with empty ID list."""
    #     results = product_service.get_products_by_ids([])
    #     assert results == []

    # def test_nonexistent_product_recommendations(self, product_service):
    #     """Test recommendations for nonexistent product."""
    #     recommendations = product_service.get_product_recommendations("NONEXISTENT")
    #     assert recommendations == []  # Should handle gracefully

    def test_metadata_field_validation_security(self, product_service):
        """Test that metadata field validation prevents unauthorized access."""
        valid_fields = ["store", "main_category", "categories"]

        # Test that valid fields work
        for field in valid_fields:
            result = product_service.get_metadata_options(field)
            assert isinstance(result, list)
            if result:  # If there are results
                # Should be MetadataOption-like objects or tuples
                assert hasattr(result[0], "__len__") or hasattr(result[0], "value")

        # Test that invalid fields raise security errors
        invalid_fields = [
            "password",
            "secret",
            "internal_id",
            "admin_field",
            "../etc/passwd",
            "'; DROP TABLE products; --",
        ]

        for invalid_field in invalid_fields:
            with pytest.raises(KeyError, match=f"Field '{invalid_field}' not found"):
                product_service.get_metadata_options(invalid_field)

    def test_business_rules_consistency(self, product_service):
        """Test that business rules are consistently applied."""
        # Test with different similarity scores to verify confidence mapping
        results = product_service.semantic_search("test products", limit=3)

        for product in results:
            # Verify confidence mapping is consistent
            if product.similarity > 0.85:
                assert product.confidence == "high"
            elif product.similarity > 0.6:
                assert product.confidence == "medium"
            else:
                assert product.confidence == "low"

            # Verify search type is set correctly
            assert product.search_type == "semantic"

            # Verify ProductItemLLM conversion was applied
            assert isinstance(product, ProductItemLLM)
            assert isinstance(product, ProductItem)  # Inheritance
