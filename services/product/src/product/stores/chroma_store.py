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

    # def get_by_ids(self, ids: List[str]) -> List[ProductItem]:
    #     """Direct product lookup by ASINs"""
    #     if not self._available:
    #         logger.warning("ChromaDB not available, returning empty results")
    #         return []

    #     try:
    #         results = self.collection.get(ids=ids, include=["metadatas"])

    #         if not results["metadatas"]:
    #             return []

    #         products = []
    #         for metadata in results["metadatas"]:
    #             try:
    #                 metadata["similarity"] = 1.0  # Perfect match for direct lookup
    #                 metadata["search_type"] = "direct"
    #                 product = self._create_product_from_metadata(metadata)
    #                 if product:  # Only add if creation succeeded
    #                     products.append(product)
    #             except Exception as e:
    #                 logger.warning(f"Failed to create ProductItem: {e}")
    #                 continue

    #         return products

    #     except Exception as e:
    #         logger.error(f"Get by IDs failed: {e}")
    #         return []

    # def semantic_search(
    #     self, query: str, limit: int, filters: Optional[SearchFilters] = None
    # ) -> List[ProductItem]:
    #     """
    #     Simplified semantic search using ChromaDB's native vector similarity.
    #     """
    #     if not self._available:
    #         logger.warning("ChromaDB not available, returning empty results")
    #         return []

    #     try:
    #         # Convert business filters to ChromaDB format
    #         chroma_where = self._convert_filters_to_chroma(filters) if filters else None

    #         results = self.collection.query(
    #             query_texts=[query],
    #             n_results=limit,
    #             where=chroma_where,
    #             include=["metadatas", "distances"],
    #         )

    #         return self._format_results(results, "semantic")

    #     except Exception as e:
    #         logger.error(f"Semantic search failed: {e}")
    #         return []

    # def lexical_search(
    #     self, query: str, limit: int, filters: Optional[SearchFilters] = None
    # ) -> List[ProductItem]:
    #     """
    #     Simplified lexical search using ChromaDB's document text matching.
    #     """
    #     if not self._available:
    #         logger.warning("ChromaDB not available, returning empty results")
    #         return []

    #     try:
    #         # Convert business filters
    #         chroma_where = self._convert_filters_to_chroma(filters) if filters else None

    #         # Simple document search - look for query terms in the text
    #         where_document = {"$contains": query.lower()}

    #         results = self.collection.query(
    #             query_texts=[query],  # Still need this for distance calculation
    #             n_results=limit,
    #             where=chroma_where,
    #             where_document=where_document,
    #             include=["metadatas", "distances"],
    #         )

    #         return self._format_results(results, "lexical")

    #     except Exception as e:
    #         logger.error(f"Lexical search failed: {e}")
    #         # Fallback to semantic search if lexical fails
    #         logger.info("Falling back to semantic search")
    #         return self.semantic_search(query, limit, filters)

    # def hybrid_search(
    #     self,
    #     query: str,
    #     limit: int,
    #     filters: Optional[SearchFilters] = None,
    #     semantic_weight: float = 0.7,
    #     lexical_weight: float = 0.3,
    # ) -> List[ProductItem]:
    #     """
    #     Simplified hybrid search - get results from both methods and combine them.
    #     """
    #     if not self._available:
    #         logger.warning("ChromaDB not available, returning empty results")
    #         return []

    #     try:
    #         # Get more results from each method to have candidates for combination
    #         expanded_limit = min(limit * 2, 50)

    #         semantic_results = self.semantic_search(query, expanded_limit, filters)
    #         lexical_results = self.lexical_search(query, expanded_limit, filters)

    #         # Simple combination: collect unique products and average their scores
    #         combined_products = {}

    #         # Add semantic results
    #         for product in semantic_results:
    #             asin = product.parent_asin
    #             if asin not in combined_products:
    #                 combined_products[asin] = {
    #                     "product": product,
    #                     "semantic_score": product.similarity or 0.0,
    #                     "lexical_score": 0.0,
    #                     "count": 0,
    #                 }
    #             combined_products[asin]["count"] += 1

    #         # Add lexical results
    #         for product in lexical_results:
    #             asin = product.parent_asin
    #             if asin in combined_products:
    #                 combined_products[asin]["lexical_score"] = product.similarity or 0.0
    #             else:
    #                 combined_products[asin] = {
    #                     "product": product,
    #                     "semantic_score": 0.0,
    #                     "lexical_score": product.similarity or 0.0,
    #                     "count": 1,
    #                 }
    #             combined_products[asin]["count"] += 1

    #         # Calculate combined scores and create final products
    #         final_products = []
    #         for asin, data in combined_products.items():
    #             # Simple weighted combination
    #             combined_score = (
    #                 semantic_weight * data["semantic_score"]
    #                 + lexical_weight * data["lexical_score"]
    #             )

    #             # Create new product with combined score
    #             product = data["product"]
    #             product.similarity = combined_score
    #             product.search_type = "hybrid"
    #             final_products.append((product, combined_score))

    #         # Sort by combined score and return top results
    #         final_products.sort(key=lambda x: x[1], reverse=True)
    #         return [product for product, _ in final_products[:limit]]

    #     except Exception as e:
    #         logger.error(f"Hybrid search failed: {e}")
    #         return self.semantic_search(query, limit, filters)

    # def get_metadata_values(self, field: str) -> List[str]:
    #     """Get unique values for a metadata field - essential for filters"""
    #     if not self._available:
    #         logger.warning("ChromaDB not available, returning empty metadata values")
    #         return []

    #     try:
    #         # Get all documents with metadata
    #         all_docs = self.collection.get(include=["metadatas"])
    #         values = set()

    #         for metadata in all_docs["metadatas"]:
    #             if field in metadata and metadata[field] is not None:
    #                 # Handle different data types
    #                 value = metadata[field]
    #                 if isinstance(value, list):
    #                     values.update(str(v) for v in value)
    #                 else:
    #                     values.add(str(value))

    #         return sorted(list(values))

    #     except Exception as e:
    #         logger.error(f"Get metadata values failed for field {field}: {e}")
    #         return []

    # Private helper methods

    # def _convert_filters_to_chroma(self, filters: SearchFilters) -> Dict[str, Any]:
    #     """
    #     Convert business SearchFilters to ChromaDB where clause format.
    #     Simplified version with essential filters only.
    #     """
    #     chroma_filters = {}

    #     # Price filtering
    #     if filters.min_price is not None or filters.max_price is not None:
    #         price_filter = {}
    #         if filters.min_price is not None:
    #             price_filter["$gte"] = filters.min_price
    #         if filters.max_price is not None:
    #             price_filter["$lte"] = filters.max_price
    #         chroma_filters["price"] = price_filter

    #     # Store filtering
    #     if filters.store:
    #         chroma_filters["store"] = {"$eq": filters.store}

    #     # Category filtering
    #     if filters.main_category:
    #         chroma_filters["main_category"] = {"$eq": filters.main_category}

    #     # Rating filtering
    #     if filters.min_rating is not None:
    #         chroma_filters["average_rating"] = {"$gte": filters.min_rating}

    #     # Boolean filters
    #     if filters.has_price is not None:
    #         chroma_filters["has_price"] = filters.has_price

    #     logger.debug(f"Converted filters to ChromaDB format: {chroma_filters}")
    #     return chroma_filters
