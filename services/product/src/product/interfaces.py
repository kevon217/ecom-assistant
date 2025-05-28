# product/src/product/interfaces.py
"""
Storage-agnostic interfaces that define the contract between
business logic and storage implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import DocumentFilters, ProductItem, SearchFilters


class ProductStoreInterface(ABC):
    """
    Abstract interface for product storage backends.
    Business logic depends only on this interface, not concrete implementations.
    """

    @abstractmethod
    def semantic_search(
        self,
        query: str,
        limit: int,
        filters: Optional[SearchFilters] = None,
        document_filters: Optional[DocumentFilters] = None,
    ) -> List[ProductItem]:
        """
        Perform semantic similarity search.

        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Business filter criteria
            document_filters: Full-text substring filters on document content

        Returns:
            List of ProductItems with similarity scores
        """
        pass

    # @abstractmethod
    # def get_by_ids(self, ids: List[str]) -> List[ProductItem]:
    #     """
    #     Get products by their unique identifiers.

    #     Args:
    #         ids: List of product identifiers (ASINs)

    #     Returns:
    #         List of ProductItems
    #     """
    #     pass

    @abstractmethod
    def count(self) -> int:
        """
        Get total number of products in the store.

        Returns:
            Total product count
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the storage backend is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_metadata_values(self, field: str) -> List[tuple]:
        """
        Get metadata values with counts for the given field.

        Args:
            field: Metadata field name

        Returns:
            List of (value, count) tuples sorted by descending count
        """
        pass

    # @abstractmethod
    # def lexical_search(
    #     self, query: str, limit: int, filters: Optional[SearchFilters] = None
    # ) -> List[ProductItem]:
    #     """
    #     Perform lexical/keyword-based search.

    #     Args:
    #         query: Search query string
    #         limit: Maximum number of results
    #         filters: Business filter criteria

    #     Returns:
    #         List of ProductItems with relevance scores
    #     """
    #     pass

    # @abstractmethod
    # def hybrid_search(
    #     self,
    #     query: str,
    #     limit: int,
    #     filters: Optional[SearchFilters] = None,
    #     semantic_weight: float = 0.7,
    #     lexical_weight: float = 0.3,
    # ) -> List[ProductItem]:
    #     """
    #     Perform hybrid search combining semantic and lexical approaches.

    #     Args:
    #         query: Search query string
    #         limit: Maximum number of results
    #         filters: Business filter criteria
    #         semantic_weight: Weight for semantic similarity (0.0-1.0)
    #         lexical_weight: Weight for lexical matching (0.0-1.0)

    #     Returns:
    #         List of ProductItems with combined scores
    #     """
    #     pass
