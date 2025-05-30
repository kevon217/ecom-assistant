# product/src/product/stores/chroma_store.py
"""
Simplified ChromaDB storage implementation focused on core functionality.
Removed complex re-ranking, hybrid scoring, and advanced features for MVP.
"""

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.errors import NotFoundError
from chromadb.utils import embedding_functions

from ..interfaces import ProductStoreInterface
from ..models import DocumentFilters, ProductItem, SearchFilters

logger = logging.getLogger(__name__)


class ChromaProductStore(ProductStoreInterface):
    """
    Simplified ChromaDB implementation focusing on essential functionality:
    - Basic semantic search using ChromaDB's native vector similarity
    - Simple lexical search using document text matching
    - Straightforward hybrid search with simple score combination
    - Essential metadata retrieval for filters
    """

    def __init__(
        self, chroma_persist_dir: str, embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.client = chromadb.PersistentClient(path=chroma_persist_dir)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        self.collection = None
        self._available = False

        try:
            self.collection = self.client.get_collection(
                name="products", embedding_function=self.embedding_fn
            )
            self._available = True
            logger.info(
                f"Connected to ChromaDB collection with {self.collection.count()} products"
            )
        except (ValueError, NotFoundError) as e:
            logger.warning(
                f"ChromaDB collection not available: {e}. Store will be in unavailable state."
            )
            self._available = False

    def semantic_search(
        self,
        query: str,
        limit: int,
        filters: Optional[SearchFilters] = None,
        document_filters: Optional[DocumentFilters] = None,
    ) -> List[ProductItem]:
        """
        Perform a semantic (vector) search with optional metadata filters
        (via `filters`) and full-text substring filters (via `document_filters`).
        """
        if not self._available:
            logger.warning("ChromaDB not available, returning empty list")
            return []

        # Build metadata `where` clause
        where: Optional[Dict[str, Any]] = None
        if filters:
            where = self._convert_filters_to_chroma(filters)

        # Enhanced document where clause
        where_document: Optional[Dict[str, Any]] = None
        if document_filters:
            clauses = []

            # Basic contains/not_contains
            if document_filters.contains:
                clauses.extend([{"$contains": s} for s in document_filters.contains])
            if document_filters.not_contains:
                clauses.extend(
                    [{"$not_contains": s} for s in document_filters.not_contains]
                )

            # NEW: OR logic for contains_any
            if document_filters.contains_any:
                or_clause = {
                    "$or": [{"$contains": s} for s in document_filters.contains_any]
                }
                clauses.append(or_clause)

            # Combine clauses
            if clauses:
                if document_filters.use_or_logic:
                    where_document = {"$or": clauses}
                else:
                    where_document = (
                        {"$and": clauses} if len(clauses) > 1 else clauses[0]
                    )

        # Execute the query
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
            where_document=where_document,
            include=["metadatas", "distances"],
        )

        return self._format_results(results, "semantic")

    def count(self) -> int:
        """Get total number of products"""
        if not self._available:
            return 0

        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0

    def health_check(self) -> bool:
        """Check if ChromaDB is accessible"""
        if not self._available:
            return False

        try:
            self.collection.count()
            return True
        except Exception:
            return False

    def get_metadata_values(self, field: str) -> List[tuple]:
        """
        Return a list of (value, count) for the given metadata field,
        sorted by descending count.
        """
        if not self._available:
            return []

        # Retrieve all metadata dicts
        docs = self.collection.get(include=["metadatas"])["metadatas"]

        # Track both normalized and original case
        case_map = {}  # normalized -> original
        counter = Counter()

        for metadata in docs:
            raw = metadata.get(field)
            if raw is None:
                continue

            if isinstance(raw, list):
                for v in raw:
                    normalized = str(v).strip().lower()
                    if normalized not in case_map:
                        case_map[normalized] = str(v).strip()  # Keep first seen
                    counter[normalized] += 1
            else:
                normalized = str(raw).strip().lower()
                if normalized not in case_map:
                    case_map[normalized] = str(raw).strip()
                counter[normalized] += 1

        # Return with original case preserved
        return [(case_map[k], v) for k, v in counter.most_common()]

    # -------------------------------------------------------------------------
    #  Internal helpers
    # -------------------------------------------------------------------------
    def _convert_filters_to_chroma(self, filters: SearchFilters) -> Dict[str, Any]:
        conditions = []

        # Price filters - handle -1 sentinel value for missing prices
        price_conditions = []

        if filters.min_price is not None:
            price_conditions.append({"price": {"$gte": filters.min_price}})
        if filters.max_price is not None:
            price_conditions.append({"price": {"$lte": filters.max_price}})
        if filters.price_above is not None:
            price_conditions.append({"price": {"$gt": filters.price_above}})
        if filters.price_below is not None:
            price_conditions.append({"price": {"$lt": filters.price_below}})

        # If any price filter is applied, exclude products with price = -1 (missing price)
        if price_conditions:
            all_price_conditions = [{"price": {"$gte": 0}}] + price_conditions
            if len(all_price_conditions) > 1:
                conditions.append({"$and": all_price_conditions})
            else:
                conditions.append(all_price_conditions[0])

        # Store filters - exact match
        if filters.store is not None:
            if isinstance(filters.store, list):
                if filters.store:  # Only add if we have values
                    conditions.append({"store": {"$in": filters.store}})
            else:
                conditions.append({"store": {"$eq": filters.store}})

        if filters.exclude_stores:
            conditions.append({"store": {"$nin": filters.exclude_stores}})

        # Category filters - exact match
        if filters.main_category is not None:
            if isinstance(filters.main_category, list):
                if filters.main_category:
                    conditions.append({"main_category": {"$in": filters.main_category}})
            else:
                conditions.append({"main_category": {"$eq": filters.main_category}})

        if filters.exclude_categories:
            conditions.append({"main_category": {"$nin": filters.exclude_categories}})

        # Rating filters
        if filters.min_rating is not None:
            conditions.append({"average_rating": {"$gte": filters.min_rating}})
        if filters.max_rating is not None:
            conditions.append({"average_rating": {"$lte": filters.max_rating}})

        # Review count filters - removed has_reviews, use explicit rating_number comparisons instead

        # Build final where clause according to ChromaDB rules
        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _format_results(self, chroma_results, search_type: str) -> List[ProductItem]:
        """Convert ChromaDB results to ProductItem objects - simplified version"""
        products = []

        if not chroma_results["ids"] or not chroma_results["ids"][0]:
            return products

        for i in range(len(chroma_results["ids"][0])):
            try:
                metadata = chroma_results["metadatas"][0][i].copy()
                distance = chroma_results["distances"][0][i]

                # Convert ChromaDB distance to similarity (simple conversion)
                similarity = max(0.0, min(1.0, 1.0 - distance))

                # Add computed fields
                metadata["similarity"] = similarity
                metadata["search_type"] = search_type

                product = self._create_product_from_metadata(metadata)
                if product:  # Only add if creation succeeded
                    products.append(product)

            except Exception as e:
                logger.warning(f"Failed to process search result {i}: {e}")
                continue

        return products

    def _create_product_from_metadata(
        self, metadata: Dict[str, Any]
    ) -> Optional[ProductItem]:
        """Create ProductItem from ChromaDB metadata with robust error handling"""
        try:
            # Helper functions for safe conversion
            def safe_str(value, default=""):
                if value is None or (
                    isinstance(value, float) and value != value
                ):  # NaN check
                    return default
                return str(value)

            def safe_float(value, default=0.0):
                if value is None or (
                    isinstance(value, float) and value != value
                ):  # NaN check
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default

            def safe_int(value, default=0):
                if value is None or (
                    isinstance(value, float) and value != value
                ):  # NaN check
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default

            def safe_list(value, default=None):
                if default is None:
                    default = []
                if value is None:
                    return default
                if isinstance(value, list):
                    return value
                # Handle JSON strings from ChromaDB
                if isinstance(value, str):
                    try:
                        import json

                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            return parsed
                    except:
                        pass
                return default

            def safe_dict(value, default=None):
                if default is None:
                    default = {}
                if value is None:
                    return default
                if isinstance(value, dict):
                    return value
                # Handle JSON strings from ChromaDB
                if isinstance(value, str):
                    try:
                        import json

                        parsed = json.loads(value)
                        if isinstance(parsed, dict):
                            return parsed
                    except:
                        pass
                return default

            # Clean and validate metadata
            clean_metadata = {
                "parent_asin": safe_str(metadata.get("parent_asin"), "UNKNOWN"),
                "title": safe_str(metadata.get("title"), "Unknown Product"),
                "title_raw": safe_str(metadata.get("title_raw")),
                "price": safe_float(metadata.get("price")),
                "average_rating": safe_float(metadata.get("average_rating")),
                "rating_number": safe_int(metadata.get("rating_number")),
                "store": safe_str(metadata.get("store"), "Unknown Store"),
                "main_category": safe_str(
                    metadata.get("main_category"), "Unknown Category"
                ),
                "categories": safe_list(metadata.get("categories_raw")),
                "features": safe_list(metadata.get("features_raw")),
                "description": safe_list(metadata.get("description_raw")),
                "details": safe_dict(metadata.get("details_raw")),
                "similarity": safe_float(metadata.get("similarity")),
                "search_type": safe_str(metadata.get("search_type")),
                "confidence": metadata.get("confidence"),  # Keep None if None
            }

            return ProductItem(**clean_metadata)

        except Exception as e:
            logger.warning(f"Failed to create ProductItem from metadata: {e}")
            logger.debug(f"Problematic metadata: {metadata}")
            return None
