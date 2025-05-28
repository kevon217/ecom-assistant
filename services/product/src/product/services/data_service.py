# product/src/product/data_service_clean.py
"""
Completely storage-agnostic business logic layer.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import ProductStoreInterface
from ..models import (
    DocumentFilters,
    MetadataOption,
    ProductItem,
    ProductItemLLM,
    SearchFilters,
)

logger = logging.getLogger(__name__)


class ProductDataService:
    """
    Pure business logic layer that depends only on the ProductStoreInterface.
    Can work with any storage backend that implements the interface.
    """

    def __init__(self, store: ProductStoreInterface):
        self.store = store  # Depends on interface, not concrete implementation

        # Pure business configuration
        self.max_results_limit = 100

        # Initialize search statistics tracking
        self.search_stats = {"semantic": 0}  # Removed lexical/hybrid counters

        logger.info(
            f"ProductDataService initialized with {self.store.count()} products"
        )

    def semantic_search(
        self,
        query: str,
        limit: int,
        # offset: int = 0, #TODO: figure out pagination capabilities in later versions
        filters: Optional[SearchFilters] = None,
        document_filters: Optional[DocumentFilters] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> List[ProductItemLLM]:  # ✅ FIX: Return ProductItemLLM
        # ✅ ADD: Validation and business logic
        self._validate_search_params(query, limit)
        limit = min(limit, self.max_results_limit)

        # ✅ ADD: Track search statistics
        self.search_stats["semantic"] += 1

        # Normalize the query itself
        normalized_query = query.strip().lower()

        # Fetch extra items to allow slicing for offset
        # fetch_count = limit + offset #TODO: figure out pagination capabilities in later versions

        items = self.store.semantic_search(
            query=normalized_query,
            # limit=fetch_count,
            limit=limit,
            filters=filters,
            document_filters=document_filters,
        )

        # ✅ ADD: Apply business rules (confidence scoring)
        items = self._apply_business_rules(items, "semantic")

        # Optional post‐sort on metadata field
        if sort_by:
            reverse = sort_order == "desc"
            items.sort(
                key=lambda p: getattr(p, sort_by, float("-inf")),
                reverse=reverse,
            )

        # ✅ ADD: Convert to LLM format (80% token reduction)
        # paginated_items = items[offset : offset + limit] #TODO: figure out pagination capabilities in later versions
        llm_results = [ProductItemLLM.from_product_item(item) for item in items]

        logger.info(
            f"Semantic search for '{query}' returned {len(llm_results)} results"
        )
        return llm_results

    def get_metadata_options(
        self,
        field_name: str,
        *,
        limit: Optional[int] = None,
        sort_by_count: bool = True,
    ) -> List[MetadataOption]:
        # ✅ ADD: Restrict to valid fields (restore previous security)
        valid_fields = ["store", "main_category", "categories"]
        if field_name not in valid_fields:
            raise KeyError(
                f"Field '{field_name}' not found. Valid fields: {valid_fields}"
            )

        raw = self.store.get_metadata_values(field_name)
        if not sort_by_count:
            raw = sorted(raw, key=lambda vc: vc[0])
        if limit is not None:
            raw = raw[:limit]
        return [MetadataOption(value=v, count=c) for v, c in raw]

    # Pure business methods
    def _validate_search_params(self, query: str, limit: int):
        """Business validation logic"""
        if not query.strip():
            raise ValueError("Query cannot be empty")

        if limit <= 0:
            raise ValueError("Limit must be positive")

    def _apply_business_rules(
        self, results: List[ProductItem], search_type: str
    ) -> List[ProductItem]:
        """Apply business rules to search results"""
        for product in results:
            # Business rule: confidence scoring
            if product.similarity > 0.85:
                product.confidence = "high"
            elif product.similarity > 0.6:
                product.confidence = "medium"
            else:
                product.confidence = "low"

            # Business context
            product.search_type = search_type

        return results

    def get_search_statistics(self) -> Dict[str, Any]:
        """Business analytics"""
        total_searches = sum(self.search_stats.values())

        return {
            "total_searches": total_searches,
            "search_breakdown": self.search_stats.copy(),
            "search_percentages": {
                search_type: (count / total_searches * 100) if total_searches > 0 else 0
                for search_type, count in self.search_stats.items()
            },
            "store_health": self.store.health_check(),
            "total_products": self.store.count(),
        }

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get available filter options for UI"""
        return {
            "stores": self.store.get_metadata_values("store"),
            "main_categories": self.store.get_metadata_values("main_category"),
        }

    # def get_metadata_options(self, field_name: str) -> List[str]:
    #     """Get unique values for a specific metadata field (for API endpoint)"""
    #     valid_fields = ["store", "main_category", "categories"]
    #     if field_name not in valid_fields:
    #         raise KeyError(
    #             f"Field '{field_name}' not found. Valid fields: {valid_fields}"
    #         )
    #     return self.store.get_metadata_values(field_name)

    # def lexical_search(
    #     self, query: str, limit: int = 10, filters: Optional[SearchFilters] = None
    # ) -> List[ProductItemLLM]:
    #     """Pure business logic - storage-agnostic"""
    #     self._validate_search_params(query, limit)
    #     limit = min(limit, self.max_results_limit)

    #     self.search_stats["lexical"] += 1

    #     # Store handles all lexical search implementation
    #     results = self.store.lexical_search(query, limit, filters)
    #     results = self._apply_business_rules(results, "lexical")

    #     # Convert to LLM-optimized format
    #     llm_results = [ProductItemLLM.from_product_item(item) for item in results]

    #     logger.info(f"Lexical search for '{query}' returned {len(llm_results)} results")
    #     return llm_results

    # def hybrid_search(
    #     self,
    #     query: str,
    #     limit: int = 10,
    #     filters: Optional[SearchFilters] = None,
    #     semantic_weight: Optional[float] = None,
    #     lexical_weight: Optional[float] = None,
    # ) -> List[ProductItemLLM]:
    #     """Pure business logic with weight normalization"""
    #     self._validate_search_params(query, limit)
    #     limit = min(limit, self.max_results_limit)

    #     # Business rule: normalize weights
    #     sem_weight = semantic_weight or self.default_search_weights["semantic"]
    #     lex_weight = lexical_weight or self.default_search_weights["lexical"]

    #     total_weight = sem_weight + lex_weight
    #     if total_weight != 1.0:
    #         sem_weight = sem_weight / total_weight
    #         lex_weight = lex_weight / total_weight
    #         logger.info(
    #             f"Normalized weights: semantic={sem_weight:.2f}, lexical={lex_weight:.2f}"
    #         )

    #     self.search_stats["hybrid"] += 1

    #     # Store handles all hybrid implementation details
    #     results = self.store.hybrid_search(
    #         query, limit, filters, sem_weight, lex_weight
    #     )
    #     results = self._apply_business_rules(results, "hybrid")

    #     # Convert to LLM-optimized format
    #     llm_results = [ProductItemLLM.from_product_item(item) for item in results]

    #     logger.info(f"Hybrid search for '{query}' returned {len(llm_results)} results")
    #     return llm_results

    # def get_products_by_ids(self, asins: List[str]) -> List[ProductItemLLM]:
    #     """Business logic for batch product lookup"""
    #     if not asins:
    #         return []

    #     # Business rule: limit batch size
    #     if len(asins) > 50:
    #         logger.warning(f"Batch size {len(asins)} too large, limiting to 50")
    #         asins = asins[:50]

    #     results = self.store.get_by_ids(asins)
    #     # Convert to LLM-optimized format
    #     return [ProductItemLLM.from_product_item(item) for item in results]

    # def get_product_recommendations(
    #     self, product_asin: str, limit: int = 5
    # ) -> List[ProductItemLLM]:
    #     """Business logic for product recommendations"""
    #     source_products = self.get_products_by_ids([product_asin])
    #     if not source_products:
    #         return []

    #     source_product = source_products[0]

    #     # Business logic: create recommendation query
    #     query_parts = [source_product.title]
    #     if hasattr(source_product, "features") and source_product.features:
    #         query_parts.extend(source_product.features[:3])

    #     recommendation_query = " ".join(query_parts)

    #     # Get candidates and filter out source
    #     candidates = self.semantic_search(recommendation_query, limit + 5)
    #     recommendations = [p for p in candidates if p.parent_asin != product_asin]

    #     return recommendations[:limit]

    # def semantic_search(
    #     self, query: str, limit: int = 10, filters: Optional[SearchFilters] = None
    # ) -> List[ProductItemLLM]:
    #     """Pure business logic - no storage implementation details"""
    #     self._validate_search_params(query, limit)
    #     limit = min(limit, self.max_results_limit)

    #     self.search_stats["semantic"] += 1

    #     # Store handles ALL the implementation details
    #     results = self.store.semantic_search(query, limit, filters)

    #     # Apply business rules
    #     results = self._apply_business_rules(results, "semantic")

    #     # Convert to LLM-optimized format (80% token reduction)
    #     llm_results = [ProductItemLLM.from_product_item(item) for item in results]

    #     logger.info(
    #         f"Semantic search for '{query}' returned {len(llm_results)} results"
    #     )
    #     return llm_results
