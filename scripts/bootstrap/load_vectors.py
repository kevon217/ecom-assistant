# Enhanced pipeline integration for ChromaDB

# 1. UPDATED load_vectors.py for simplified ChromaDB architecture
# scripts/bootstrap/load_vectors.py

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Add paths for service models
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / "services" / "product" / "src"))

from product.models import ProductItem, SearchFilters
from product.stores.chroma_store import ChromaProductStore

logger = logging.getLogger(__name__)


class ChromaBootstrapper:
    """
    Enhanced bootstrapper that works with our simplified ChromaDB architecture.
    Validates data against Pydantic models during the loading process.
    """

    def __init__(
        self,
        csv_path: str,
        persist_dir: str,
        collection_name: str = "products",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.csv_path = Path(csv_path)
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        # Stats tracking
        self.stats = {
            "total_rows": 0,
            "processed_rows": 0,
            "validation_errors": 0,
            "skipped_rows": 0,
            "duplicate_asins": 0,
        }

    def load_and_validate_data(self) -> pd.DataFrame:
        """
        Load CSV and perform validation that complements your data cleaning pipeline.
        """
        logger.info(f"Loading data from {self.csv_path}")
        df = pd.read_csv(self.csv_path)
        self.stats["total_rows"] = len(df)

        logger.info(f"Loaded {len(df)} rows from cleaned CSV")

        # 1. Check for required columns
        required_cols = [
            "parent_asin",
            "title_raw",
            "price",
            "average_rating",
            "rating_number",
            "store",
            "__embed_text",
        ]

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # 2. Validate embed text (critical for ChromaDB)
        logger.info("Validating embed text quality...")
        invalid_embed = df[
            df["__embed_text"].isna()
            | (df["__embed_text"].str.strip() == "")
            | (df["__embed_text"].str.len() < 10)  # Minimum meaningful text
        ]

        if len(invalid_embed) > 0:
            logger.warning(f"Found {len(invalid_embed)} rows with invalid embed text")
            self.stats["skipped_rows"] += len(invalid_embed)
            df = df.drop(invalid_embed.index)

        # 3. Handle duplicate ASINs (ChromaDB needs unique IDs)
        logger.info("Checking for duplicate ASINs...")
        duplicate_asins = df[df["parent_asin"].duplicated()]
        if len(duplicate_asins) > 0:
            logger.warning(
                f"Found {len(duplicate_asins)} duplicate ASINs, keeping first occurrence"
            )
            self.stats["duplicate_asins"] = len(duplicate_asins)
            df = df.drop_duplicates(subset=["parent_asin"], keep="first")

        # 4. Validate sample against Pydantic model
        logger.info("Validating sample rows against ProductItem model...")
        validation_errors = []

        # Test first 100 rows for model compatibility
        sample_size = min(100, len(df))
        for idx in range(sample_size):
            row = df.iloc[idx]
            try:
                self._create_product_item(row)
            except Exception as e:
                validation_errors.append(
                    {
                        "row_index": idx,
                        "asin": row.get("parent_asin", "UNKNOWN"),
                        "error": str(e),
                    }
                )

        if validation_errors:
            logger.warning(
                f"Found {len(validation_errors)} validation errors in sample"
            )
            self.stats["validation_errors"] = len(validation_errors)

            # Log first few errors for debugging
            for error in validation_errors[:3]:
                logger.warning(
                    f"Validation error at row {error['row_index']}: {error['error']}"
                )
        else:
            logger.info("✅ All sample rows passed Pydantic validation")

        self.stats["processed_rows"] = len(df)
        return df

    def _create_product_item(self, row: pd.Series) -> ProductItem:
        """
        Create ProductItem from DataFrame row with enhanced error handling.
        This validates the cleaning pipeline output.
        """

        # Safe parsing helpers
        def safe_float(value, default=0.0):
            if pd.isna(value):
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        def safe_int(value, default=0):
            if pd.isna(value):
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        def safe_list(value):
            if pd.isna(value):
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    import ast

                    return ast.literal_eval(value)
                except:
                    return [value] if value.strip() else []
            return []

        def safe_dict(value):
            if pd.isna(value):
                return {}
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    import ast

                    return ast.literal_eval(value)
                except:
                    return {}
            return {}

        def safe_str(value, default=""):
            if pd.isna(value):
                return default
            try:
                return str(value)
            except (ValueError, TypeError):
                return default

        return ProductItem(
            parent_asin=str(row["parent_asin"]),
            title=str(row.get("title_raw", "Unknown Product")),
            title_raw=str(row.get("title_raw", "Unknown Product")),
            price=safe_float(row.get("price")),
            average_rating=safe_float(row.get("average_rating")),
            rating_number=safe_int(row.get("rating_number")),
            store=safe_str(row.get("store"), "Unknown Store"),
            main_category=safe_str(row.get("main_category"), "Unknown Category"),
            categories=safe_list(row.get("categories_raw")),
            features=safe_list(row.get("features_raw")),
            description=safe_list(row.get("description_raw")),
            details=safe_dict(row.get("details_raw")),
            # ChromaDB will set similarity during search
            similarity=0.0,
            # has_price=pd.notna(row.get("price")) and safe_float(row.get("price")) > 0,
            # has_reviews=safe_int(row.get("rating_number")) > 0,
        )

    def bootstrap_chromadb(self, df: pd.DataFrame) -> ChromaProductStore:
        """
        Bootstrap ChromaDB with validated data using our simplified architecture.
        """
        logger.info(f"Initializing ChromaDB at {self.persist_dir}")

        # Create the store (this will create the collection)
        store = ChromaProductStore(
            chroma_persist_dir=str(self.persist_dir),
            embedding_model=self.embedding_model,
        )

        # Prepare data for ChromaDB
        logger.info("Preparing data for ChromaDB insertion...")

        ids = []
        documents = []
        metadatas = []

        for idx, row in df.iterrows():
            try:
                # Use ASIN as ID (unique identifier)
                doc_id = str(row["parent_asin"])

                # Use the cleaned embed text
                document_text = str(row["__embed_text"])

                # Create rich metadata from all fields
                metadata = self._create_metadata(row)

                ids.append(doc_id)
                documents.append(document_text)
                metadatas.append(metadata)

            except Exception as e:
                logger.warning(f"Failed to prepare row {idx}: {e}")
                self.stats["skipped_rows"] += 1
                continue

        # Batch insert to ChromaDB
        logger.info(f"Inserting {len(ids)} products into ChromaDB...")

        try:
            # Create or recreate collection
            if store.collection is not None:
                # Collection exists, clear it
                existing_count = store.collection.count()
                logger.info(
                    f"Clearing existing {existing_count} products from collection"
                )
                store.client.delete_collection(self.collection_name)

            # Create fresh collection
            logger.info(f"Creating collection: {self.collection_name}")
            store.collection = store.client.create_collection(
                name=self.collection_name, embedding_function=store.embedding_fn
            )

            # Insert in batches to handle large datasets
            batch_size = 1000
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i : i + batch_size]
                batch_docs = documents[i : i + batch_size]
                batch_metas = metadatas[i : i + batch_size]

                store.collection.add(
                    ids=batch_ids, documents=batch_docs, metadatas=batch_metas
                )

                logger.info(
                    f"Inserted batch {i // batch_size + 1}/{(len(ids) + batch_size - 1) // batch_size}"
                )

            final_count = store.collection.count()
            logger.info(
                f"✅ ChromaDB bootstrap complete! {final_count} products loaded."
            )

        except Exception as e:
            logger.error(f"ChromaDB insertion failed: {e}")
            raise

        return store

    def _create_metadata(self, row: pd.Series) -> Dict[str, Any]:
        """
        Create comprehensive metadata for ChromaDB storage.
        This includes all the fields needed for filtering and business logic.
        """

        # Helper functions
        def safe_convert(value, target_type, default=None):
            if pd.isna(value):
                return default
            try:
                if target_type == float:
                    return float(value)
                elif target_type == int:
                    return int(value)
                elif target_type == str:
                    return str(value)
                elif target_type == list:
                    if isinstance(value, list):
                        return value
                    if isinstance(value, str):
                        import ast

                        return ast.literal_eval(value)
                    return [value]
                elif target_type == dict:
                    if isinstance(value, dict):
                        return value
                    if isinstance(value, str):
                        import ast

                        return ast.literal_eval(value)
                    return {}
            except:
                return default

        def safe_json_str(value, default=""):
            """Convert complex objects to JSON strings for ChromaDB compatibility"""
            if pd.isna(value):
                return default
            try:
                import json

                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                elif isinstance(value, str):
                    # Try to parse and re-serialize to ensure valid JSON
                    try:
                        import ast

                        parsed = ast.literal_eval(value)
                        return json.dumps(parsed)
                    except:
                        return value  # Return as-is if can't parse
                else:
                    return str(value)
            except:
                return default

        metadata = {
            # Required fields
            "parent_asin": str(row["parent_asin"]),
            "title": str(row.get("title_raw", "")),
            "title_raw": str(row.get("title_raw", "")),
            # Numeric fields for filtering
            "price": safe_convert(row.get("price"), float, 0.0),
            "average_rating": safe_convert(row.get("average_rating"), float, 0.0),
            "rating_number": safe_convert(row.get("rating_number"), int, 0),
            # Categorical fields
            "store": safe_convert(row.get("store"), str, "Unknown Store").strip(),
            "main_category": safe_convert(
                row.get("main_category"), str, "Unknown Category"
            ).strip(),
            # Structured fields (JSON serialized for ChromaDB compatibility)
            "categories_raw": safe_json_str(row.get("categories_raw"), "[]"),
            "features_raw": safe_json_str(row.get("features_raw"), "[]"),
            "description_raw": safe_json_str(row.get("description_raw"), "[]"),
            "details_raw": safe_json_str(row.get("details_raw"), "{}"),
            # Computed boolean fields for efficient filtering
            "has_price": pd.notna(row.get("price"))
            and safe_convert(row.get("price"), float, 0.0) > 0,
            "has_reviews": safe_convert(row.get("rating_number"), int, 0) > 0,
            "has_description": len(safe_convert(row.get("description_raw"), list, []))
            > 0,
            "has_features": len(safe_convert(row.get("features_raw"), list, [])) > 0,
            # For debugging and checksums
            "embed_checksum": str(row.get("embed_checksum", "")),
        }

        # Add normalized text fields if they exist
        if "title_norm" in row and pd.notna(row["title_norm"]):
            metadata["title_normalized"] = str(row["title_norm"])

        if "features_norm" in row and pd.notna(row["features_norm"]):
            metadata["features_normalized"] = str(row["features_norm"])

        return metadata

    def run(self) -> ChromaProductStore:
        """Run the complete bootstrap process"""
        logger.info("Starting ChromaDB bootstrap process...")

        # Load and validate data
        df = self.load_and_validate_data()

        # Bootstrap ChromaDB
        store = self.bootstrap_chromadb(df)

        # Test the store
        logger.info("Testing ChromaDB functionality...")
        test_results = store.semantic_search("test product", 5)
        logger.info(f"Test search returned {len(test_results)} results")

        # Print final stats
        logger.info("Bootstrap Statistics:")
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")

        return store


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Bootstrap ChromaDB with product data")
    parser.add_argument("--csv", required=True, help="Path to cleaned products CSV")
    parser.add_argument(
        "--persist-dir", required=True, help="ChromaDB persistence directory"
    )
    parser.add_argument("--collection", default="products", help="Collection name")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Embedding model")

    args = parser.parse_args()

    try:
        bootstrapper = ChromaBootstrapper(
            csv_path=args.csv,
            persist_dir=args.persist_dir,
            collection_name=args.collection,
            embedding_model=args.model,
        )

        store = bootstrapper.run()
        logger.info("✅ ChromaDB bootstrap completed successfully!")

    except Exception as e:
        logger.error(f"❌ Bootstrap failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
