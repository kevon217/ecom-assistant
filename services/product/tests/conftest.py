# services/product/tests/conftest.py
"""
Shared test configuration and fixtures for product service tests.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

import pytest


# Configure Python path for testing
def setup_python_path():
    """Set up Python path to allow imports from both service and shared libs."""
    # Get absolute paths
    project_root = Path(__file__).parent.parent.parent.parent.absolute()
    product_src = Path(__file__).parent.parent / "src"
    libs_path = project_root / "libs"

    # Add paths to sys.path if not already present
    paths_to_add = [str(product_src), str(libs_path), str(project_root)]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)


# Set up paths immediately when module is imported
setup_python_path()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["PYTEST_CURRENT_TEST"] = "true"
    os.environ["TESTING"] = "true"
    os.environ["CHROMA_PERSIST_DIR"] = "/tmp/test_chroma"


@pytest.fixture
def mock_chroma_store():
    """Smart mock ChromaDB store for integration testing."""
    from src.product.interfaces import ProductStoreInterface
    from src.product.models import (
        DocumentFilters,
        ProductItem,
        ProductItemLLM,
        SearchFilters,
    )

    class MockStore(ProductStoreInterface):
        def __init__(self):
            self.test_products = [
                ProductItem(
                    parent_asin="B001TEST",
                    title="Wireless Test Headphones",
                    title_raw="wireless test headphones",
                    price=99.99,
                    average_rating=4.5,
                    rating_number=100,
                    store="TestStore",
                    main_category="Electronics",
                    categories=["Electronics", "Audio"],
                    similarity=0.95,
                    description=["High quality wireless headphones"],
                    details={"brand": "TestBrand", "model": "WH-1000"},
                    search_type="semantic",
                    confidence="high",
                ),
                ProductItem(
                    parent_asin="B002TEST",
                    title="Kitchen Test Appliance",
                    title_raw="kitchen test appliance",
                    price=49.99,
                    average_rating=4.0,
                    rating_number=50,
                    store="TestStore",
                    main_category="Home",
                    categories=["Home", "Kitchen"],
                    similarity=0.75,
                    description=["Useful kitchen appliance"],
                    details={"brand": "TestBrand", "model": "KA-100"},
                    search_type="semantic",
                    confidence="medium",
                ),
                ProductItem(
                    parent_asin="B003TEST",
                    title="Bluetooth Speaker System",
                    title_raw="bluetooth speaker system",
                    price=149.99,
                    average_rating=4.8,
                    rating_number=200,
                    store="AnotherStore",
                    main_category="Electronics",
                    categories=["Electronics", "Audio"],
                    similarity=0.85,
                    description=["Portable bluetooth speaker"],
                    details={"brand": "TestBrand", "model": "BT-500"},
                    search_type="semantic",
                    confidence="high",
                ),
            ]

        def semantic_search(
            self,
            query: str,
            limit: int,
            filters: Optional[SearchFilters] = None,
            document_filters: Optional[DocumentFilters] = None,
        ) -> List[ProductItem]:
            """Smart semantic search based on query content."""
            results = []
            query_lower = query.lower()

            # Query-dependent behavior
            if "wireless" in query_lower or "headphones" in query_lower:
                # Return wireless/audio products first
                candidates = [
                    p
                    for p in self.test_products
                    if "wireless" in p.title.lower() or "audio" in (p.categories or [])
                ]
                results.extend(candidates)
            elif "kitchen" in query_lower or "home" in query_lower:
                # Return home/kitchen products
                candidates = [
                    p for p in self.test_products if p.main_category == "Home"
                ]
                results.extend(candidates)
            elif "bluetooth" in query_lower or "speaker" in query_lower:
                # Return bluetooth/speaker products
                candidates = [
                    p for p in self.test_products if "bluetooth" in p.title.lower()
                ]
                results.extend(candidates)
            else:
                # Default: return all products
                results = self.test_products.copy()

            # Apply filters if provided
            if filters:
                results = self._apply_filters(results, filters)

            # Apply document filters if provided
            if document_filters:
                results = self._apply_document_filters(results, document_filters)

            # Set search type and return limited results
            for product in results[:limit]:
                product.search_type = "semantic"

            return results[:limit]

        # def lexical_search(self, query, limit, filters=None):
        #     """Smart lexical search based on text matching."""
        #     results = []
        #     query_lower = query.lower()

        #     # Simple text matching in title and description
        #     for product in self.test_products:
        #         title_match = query_lower in product.title.lower()
        #         desc_match = any(query_lower in desc.lower() for desc in (product.description or []))

        #         if title_match or desc_match:
        #             # Create a copy with lexical search type
        #             product_copy = product.model_copy()
        #             product_copy.search_type = "lexical"
        #             results.append(product_copy)

        #     # Apply filters if provided
        #     if filters:
        #         results = self._apply_filters(results, filters)

        #     return results[:limit]

        # def hybrid_search(self, query, limit, filters=None, semantic_weight=0.7, lexical_weight=0.3):
        #     """Simple hybrid search combining semantic and lexical."""
        #     # Get results from both methods
        #     semantic_results = self.semantic_search(query, limit * 2, filters)
        #     lexical_results = self.lexical_search(query, limit * 2, filters)

        #     # Simple combination by ASIN
        #     combined = {}

        #     # Add semantic results
        #     for product in semantic_results:
        #         combined[product.parent_asin] = product.model_copy()
        #         combined[product.parent_asin].search_type = "hybrid"

        #     # Merge with lexical results
        #     for product in lexical_results:
        #         if product.parent_asin in combined:
        #             # Already have this product, keep it as hybrid
        #             pass
        #         else:
        #             # New product from lexical search
        #             product_copy = product.model_copy()
        #             product_copy.search_type = "hybrid"
        #             combined[product.parent_asin] = product_copy

        #     return list(combined.values())[:limit]

        # def get_by_ids(self, ids):
        #     """Get products by ASINs."""
        #     return [p for p in self.test_products if p.parent_asin in ids]

        def count(self):
            """Return total product count."""
            return len(self.test_products)

        def health_check(self):
            """Always healthy for mock."""
            return True

        def get_metadata_values(self, field: str) -> List[tuple]:
            """Get unique values for metadata field."""
            if field == "store":
                return [("TestStore", 150), ("AnotherStore", 75)]
            elif field == "main_category":
                return [("Electronics", 200), ("Home", 25)]
            elif field == "categories":
                return [
                    ("Electronics", 200),
                    ("Audio", 150),
                    ("Home", 25),
                    ("Kitchen", 25),
                ]
            return []

        def _apply_filters(self, products, filters):
            """Apply business filters to product list."""
            filtered = []

            for product in products:
                # Price filters
                if filters.min_price is not None and product.price < filters.min_price:
                    continue
                if filters.max_price is not None and product.price > filters.max_price:
                    continue

                # Enhanced price filters ($gt/$lt operators)
                if (
                    filters.price_above is not None
                    and product.price <= filters.price_above
                ):
                    continue
                if (
                    filters.price_below is not None
                    and product.price >= filters.price_below
                ):
                    continue

                # Store filter - handle both string and list formats
                if filters.store:
                    if isinstance(filters.store, list):
                        if product.store not in filters.store:
                            continue
                    else:
                        if product.store != filters.store:
                            continue

                # Exclude stores filter
                if filters.exclude_stores and product.store in filters.exclude_stores:
                    continue

                # Category filter - handle both string and list formats
                if filters.main_category:
                    if isinstance(filters.main_category, list):
                        if product.main_category not in filters.main_category:
                            continue
                    else:
                        if product.main_category != filters.main_category:
                            continue

                # Exclude categories filter
                if (
                    filters.exclude_categories
                    and product.main_category in filters.exclude_categories
                ):
                    continue

                # Rating filters
                if (
                    filters.min_rating is not None
                    and product.average_rating < filters.min_rating
                ):
                    continue
                if (
                    filters.max_rating is not None
                    and product.average_rating > filters.max_rating
                ):
                    continue

                # Boolean filters
                # if filters.has_reviews is not None:
                #     has_reviews = product.rating_number > 0
                #     if filters.has_reviews != has_reviews:
                #         continue

                filtered.append(product)

            return filtered

        def _apply_document_filters(self, products, document_filters):
            """Apply document-level text filters to product list."""
            filtered = []

            for product in products:
                # Get searchable text from product
                searchable_text = self._get_searchable_text(product)

                match = True
                conditions = []

                # Contains - ALL must be present
                if document_filters.contains:
                    for term in document_filters.contains:
                        conditions.append(term.lower() in searchable_text)

                # Not contains - NONE must be present
                if document_filters.not_contains:
                    for term in document_filters.not_contains:
                        conditions.append(term.lower() not in searchable_text)

                # Contains any - ANY must be present (OR logic)
                if document_filters.contains_any:
                    any_match = any(
                        term.lower() in searchable_text
                        for term in document_filters.contains_any
                    )
                    conditions.append(any_match)

                # Apply logic combination
                if conditions:
                    if document_filters.use_or_logic:
                        match = any(conditions)
                    else:
                        match = all(conditions)

                if match:
                    filtered.append(product)

            return filtered

        def _get_searchable_text(self, product):
            """Get searchable text from product for document filtering."""
            text_parts = [
                product.title.lower(),
                product.title_raw.lower() if product.title_raw else "",
            ]

            if product.description:
                text_parts.extend([desc.lower() for desc in product.description])

            if product.categories:
                text_parts.extend([cat.lower() for cat in product.categories])

            return " ".join(text_parts)

    return MockStore()


@pytest.fixture
def test_client(mock_chroma_store):
    """Create test client with mocked dependencies."""
    from fastapi.testclient import TestClient

    from src.product.app import app
    from src.product.services.data_service import ProductDataService

    # Override the service with mock store
    app.state.product_service = ProductDataService(store=mock_chroma_store)

    return TestClient(app)


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "parent_asin": "B001TEST",
        "title": "Test Product",
        "price": 99.99,
        "average_rating": 4.5,
        "rating_number": 100,
        "store": "TestStore",
        "main_category": "Electronics",
        "categories": ["Electronics", "Gadgets"],
        "similarity": 0.9,
        "description": ["High quality test product"],
        "details": {"brand": "TestBrand", "model": "TestModel"},
    }


@pytest.fixture
def sample_search_filters():
    """Sample search filters for testing."""
    from src.product.models import DocumentFilters, MetadataOption, SearchFilters

    return SearchFilters(
        min_price=10.0,
        max_price=100.0,
        store="TestStore",
        main_category="Electronics",
        min_rating=4.0,
        # has_reviews=True,
    )


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Add any cleanup logic here if needed
    pass
