"""Product service configuration."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class ProductConfig(BaseSettings):
    """Product service specific configuration."""

    # Service settings
    port: int = Field(8003, env="PORT")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Data settings
    data_path: str = Field(
        "data/products_cleaned.csv",
        env="PRODUCT_DATA_PATH",
        description="Path to products CSV file",
    )

    # ChromaDB settings
    chroma_persist_dir: str = Field(
        "data/chroma",
        env="CHROMA_PERSIST_DIR",
        description="ChromaDB persistence directory",
    )

    # Embedding Configuration
    embedding_model: str = Field(
        "all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL",
        description="Sentence transformer model for embeddings",
    )
    embedding_normalize: bool = Field(
        True,
        env="EMBEDDING_NORMALIZE",
        description="Normalize embeddings for better similarity search",
    )
    embedding_dimensions: Optional[int] = Field(
        None,
        env="EMBEDDING_DIMENSIONS",
        description="Embedding dimensions (auto-detected if None)",
    )

    # ChromaDB Advanced Configuration
    chroma_distance_function: str = Field(
        "cosine",
        env="CHROMA_DISTANCE_FUNCTION",
        description="Distance function: cosine, l2, or ip",
    )
    chroma_hnsw_m: int = Field(
        16,
        env="CHROMA_HNSW_M",
        description="HNSW parameter M (connections per node)",
    )
    chroma_hnsw_ef_construction: int = Field(
        200,
        env="CHROMA_HNSW_EF_CONSTRUCTION",
        description="HNSW parameter ef_construction (search width during indexing)",
    )
    chroma_hnsw_ef_search: int = Field(
        100,
        env="CHROMA_HNSW_EF_SEARCH",
        description="HNSW parameter ef_search (search width during querying)",
    )

    # Optional OpenAI key (not used by product service)
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton instance
config = ProductConfig()
