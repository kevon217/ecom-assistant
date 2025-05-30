# services/product/src/product/models.py
"""
Product search models designed to help you find exactly what users are looking for.
Use these tools to search products, filter results, and provide helpful recommendations.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

# -------------------------------------------------------------------------
# PRODUCT ITEM MODELS
# -------------------------------------------------------------------------


class ProductItem(BaseModel):
    """
    Complete product information including all available details.

    When searching products, you'll receive these fields to help users make informed decisions.
    Focus on the most relevant fields for the user's needs: title, price, rating, and key features.
    """

    # Core identifiers
    parent_asin: str = Field(
        ...,
        description="Unique product identifier you can use to reference specific items",
        example="B08N5WRWNB",
    )

    # Title fields
    title: str = Field(
        ...,
        description="Product name to display to users - this is what they'll see first",
        example="Sony WH-1000XM4 Wireless Noise Canceling Headphones",
    )
    title_raw: Optional[str] = Field(
        None,
        description="Original product title if you need the unprocessed version",
    )

    # Pricing
    price: Optional[float] = Field(
        None,
        ge=0,
        description="Current price in USD - use this to help users find products within budget. None means price not available.",
        example=349.99,
    )

    # Ratings
    average_rating: Optional[float] = Field(
        None,
        ge=0,
        le=5,
        description="Customer rating from 0-5 stars - higher ratings indicate satisfied customers. None means unrated.",
        example=4.4,
    )
    rating_number: int = Field(
        ...,
        ge=0,
        description="How many customers have rated this product - more ratings = more reliable score",
        example=15234,
    )

    # Store and category
    store: str = Field(
        ...,
        description="Brand or manufacturer name - helps users find trusted brands",
        example="sony",
    )
    main_category: Optional[str] = Field(
        None,
        description="Product type/category - useful for browsing similar items",
        example="electronics",
    )
    categories: Optional[List[str]] = Field(
        None,
        description="Category path showing where this product belongs in the catalog",
        example=["Electronics", "Headphones", "Over-Ear Headphones"],
    )

    # Product details
    features: Optional[List[str]] = Field(
        None,
        description="Key product features and benefits to highlight for users",
        example=["30-hour battery life", "Active noise cancellation", "Touch controls"],
    )
    description: Optional[List[str]] = Field(
        None,
        description="Detailed product information to share when users want more details",
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Technical specifications for users who need specific details",
    )

    # Search relevance fields
    similarity: float = Field(
        ...,
        ge=0,
        le=1,
        description="How well this product matches the search (0-1) - prioritize higher scores",
        example=0.89,
    )
    confidence: Optional[str] = Field(
        None,
        description="How confident you should be that this product meets the user's needs",
        pattern="^(high|medium|low)$",
        example="high",
    )
    search_type: Optional[str] = Field(
        None,
        description="How this product was found - helps explain search results to users",
        # pattern="^(semantic|lexical|hybrid|direct)$",
        example="semantic",
    )

    @field_validator("price", "average_rating")
    def validate_sentinel_or_valid_range(cls, v, info: ValidationInfo):
        """Ensure value is either sentinel (-1) or in valid range"""
        if v == -1:
            return v
        if info.field_name == "price" and v < 0:
            raise ValueError("Price must be -1 (missing) or >= 0")
        if info.field_name == "average_rating" and (v < 0 or v > 5):
            raise ValueError("Rating must be -1 (missing) or 0-5")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "parent_asin": "B08N5WRWNB",
                "title": "Sony WH-1000XM4 Wireless Noise Canceling Headphones",
                "price": 349.99,
                "average_rating": 4.4,
                "rating_number": 15234,
                "store": "sony",
                "main_category": "electronics",
                "similarity": 0.89,
                "confidence": "high",
                "search_type": "semantic",
            }
        }
    )


class ProductItemLLM(ProductItem):
    """
    Streamlined product information optimized for clear, concise responses.

    Use this format when returning search results to users. It includes all essential
    information while keeping responses focused and easy to read.
    """

    @classmethod
    def from_product_item(cls, item: ProductItem) -> "ProductItemLLM":
        """Convert internal ProductItem to LLM-optimized version."""
        # Explicitly exclude fields during conversion
        # data = item.model_dump(exclude={"details", "features", "title_raw"})
        data = item.model_dump(exclude={"features", "title_raw"})
        return cls(**data)


# -------------------------------------------------------------------------
# SEARCH FILTER MODELS
# -------------------------------------------------------------------------


class SearchFilters(BaseModel):
    """
    Smart filters to narrow down product searches based on what users care about.

    Use these filters to help users find products that match their specific requirements:
    - Budget constraints (price filters)
    - Quality preferences (rating filters)
    - Brand preferences (store filters)
    - Product categories (category filters)

    Pro tip: Start broad, then add filters based on user feedback or if too many results.
    """

    # Price filters - removed has_price since it's not a real field
    min_price: Optional[float] = Field(
        None,
        ge=0,
        description="Find products costing at least this amount - good for quality/premium searches",
        example=20.0,
    )
    max_price: Optional[float] = Field(
        None,
        ge=0,
        description="Find products costing no more than this - essential for budget-conscious users",
        example=100.0,
    )
    price_above: Optional[float] = Field(
        None,
        ge=0,
        description="Find products costing MORE than this amount (exclusive) - for premium searches",
        example=50.0,
    )
    price_below: Optional[float] = Field(
        None,
        ge=0,
        description="Find products costing LESS than this amount (exclusive) - for bargain hunting",
        example=200.0,
    )

    # Rating filters
    min_rating: Optional[float] = Field(
        None,
        ge=0,
        le=5,
        description="Only show products rated this high or better - use 4.0+ for quality items",
        example=4.0,
    )
    max_rating: Optional[float] = Field(
        None,
        ge=0,
        le=5,
        description="Only show products rated this high or lower - rarely needed",
        example=5.0,
    )

    # Review count filter - removed has_reviews, use rating_number > 0 instead

    # Store filters
    store: Optional[Union[str, List[str]]] = Field(
        None,
        description="Search specific brands/stores. Use single name or list for multiple brands",
        example=["sony", "bose", "apple"],
    )
    exclude_stores: Optional[List[str]] = Field(
        None,
        description="Avoid specific brands/stores - helpful when users have bad experiences",
        example=["generic-brand"],
    )

    # Category filters
    main_category: Optional[Union[str, List[str]]] = Field(
        None,
        description="Search within specific product categories. TIP: Use get_metadata_options first to see available categories",
        example="electronics",
    )
    exclude_categories: Optional[List[str]] = Field(
        None,
        description="Avoid certain categories - useful to exclude refurbished, used, or unwanted types",
        example=["refurbished", "used"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "Budget search: Quality products under $50",
                    "value": {
                        "max_price": 50.0,
                        "min_rating": 4.0,
                    },
                },
                {
                    "description": "Premium search: High-end products from top brands",
                    "value": {
                        "min_price": 200.0,
                        "store": ["sony", "bose", "apple"],
                        "min_rating": 4.5,
                    },
                },
                {
                    "description": "Smart shopping: Good products, avoid problematic sellers",
                    "value": {
                        "max_price": 100.0,
                        "min_rating": 4.0,
                        "exclude_stores": ["unknown-brand"],
                        "exclude_categories": ["refurbished"],
                    },
                },
            ]
        }
    )

    @field_validator("store", "main_category", mode="before")
    def normalize_string_or_list(cls, v):
        """Clean store/category names but preserve original case."""
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        # Filter out None and empty strings, preserving case
        cleaned = [s.strip() for s in v if s and isinstance(s, str) and s.strip()]
        return cleaned if cleaned else None

    @field_validator("exclude_stores", "exclude_categories", mode="before")
    def normalize_list(cls, v):
        """Clean exclusion lists but preserve case."""
        if v is None:
            return None
        return [s.strip() for s in v if s and s.strip()]

    @model_validator(mode="after")
    def validate_price_ranges(self):
        """Ensure price filters are logically consistent."""
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError(
                f"min_price ({self.min_price}) cannot be greater than max_price ({self.max_price})"
            )

        if (
            self.price_above is not None
            and self.price_below is not None
            and self.price_above >= self.price_below
        ):
            raise ValueError(
                f"price_above ({self.price_above}) must be less than price_below ({self.price_below})"
            )

        return self


class DocumentFilters(BaseModel):
    """
    Powerful text search within product descriptions and features.

    Use these filters to find products with specific characteristics, features, or attributes
    that might not be captured in structured data. Perfect for finding products with:
    - Specific technical features (e.g., "bluetooth 5.0", "waterproof")
    - Particular materials or components
    - Compatibility requirements
    - Brand-specific features

    Think of this as searching within the product's "story" rather than its stats.
    """

    contains: Optional[List[str]] = Field(
        None,
        min_items=1,
        description="Product MUST have ALL of these terms in its description. Use for must-have features",
        example=["wireless", "noise cancelling"],
    )
    not_contains: Optional[List[str]] = Field(
        None,
        min_items=1,
        description="Product must NOT have ANY of these terms. Use to avoid unwanted items",
        example=["refurbished", "used", "renewed"],
    )
    contains_any: Optional[List[str]] = Field(
        None,
        min_items=1,
        description="Product must have AT LEAST ONE of these terms. Perfect for brand or alternative searches",
        example=["Sony", "Bose", "Sennheiser", "Audio-Technica"],
    )
    use_or_logic: bool = Field(
        False,
        description="Advanced: Switch ALL filters to OR mode. Rarely needed - default AND mode usually works best",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "Find wireless products, exclude used items",
                    "value": {
                        "contains": ["wireless"],
                        "not_contains": ["refurbished", "used", "open box"],
                    },
                },
                {
                    "description": "Find products from specific premium audio brands",
                    "value": {
                        "contains_any": [
                            "Sony",
                            "Bose",
                            "Sennheiser",
                            "Audio-Technica",
                        ],
                        "not_contains": ["clone", "generic"],
                    },
                },
                {
                    "description": "Find gaming headsets with specific features",
                    "value": {
                        "contains": ["gaming", "microphone"],
                        "contains_any": ["7.1 surround", "RGB", "wireless"],
                    },
                },
            ]
        }
    )

    @field_validator("contains", "not_contains", "contains_any", mode="before")
    def normalize_search_terms(cls, v):
        """Normalize search terms to lowercase and remove empty strings."""
        if v is None:
            return None
        # return [term.lower().strip() for term in v if term.strip()]
        return [term.strip() for term in v if term.strip()]


# -------------------------------------------------------------------------
# METADATA MODELS
# -------------------------------------------------------------------------


class MetadataOption(BaseModel):
    """
    Shows you what values are available for filtering, and how common they are.

    When you see high counts, those are popular/common values in the catalog.
    Low counts might indicate niche or specialty items.
    """

    value: str = Field(
        ...,
        description="An available filter value you can use in your searches",
        example="electronics",
    )
    count: int = Field(
        ...,
        ge=0,
        description="How many products have this value - higher = more common",
        example=1543,
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"value": "electronics", "count": 1543}}
    )


class MetadataOptionsResponse(BaseModel):
    """
    Available options for filtering, sorted by popularity.

    Use this to discover what brands, categories, or other values exist in the catalog
    before searching. The most common values appear first.
    """

    options: List[MetadataOption] = Field(
        ...,
        description="Available values sorted by frequency - most popular first",
        min_items=0,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "options": [
                    {"value": "electronics", "count": 1543},
                    {"value": "home & kitchen", "count": 892},
                    {"value": "sports & outdoors", "count": 456},
                ]
            }
        }
    )


# -------------------------------------------------------------------------
# SEARCH REQUEST MODELS
# -------------------------------------------------------------------------


class SemanticSearchRequest(BaseModel):
    """
    Your main tool for finding products that match what users are looking for.

    This search understands natural language and user intent. Combine the query with
    filters to get precise results. Here's how to use it effectively:

    1. Start with a descriptive query that captures what the user wants
    2. Add filters to narrow results based on budget, quality, or preferences
    3. Use document_filters for specific features or requirements
    4. Sort results to highlight what matters most to the user

    Remember: Better queries lead to better results. Be specific!
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Describe what the user is looking for. Include use case, preferences, and key requirements",
        example="comfortable wireless headphones for working from home with good microphone",
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="How many results to return. Use 5-10 for focused results, 20+ for browsing",
        example=10,
    )
    filters: Optional[SearchFilters] = Field(
        None,
        description="Narrow results by price, rating, brand, or category. Start without filters, then add based on results",
    )
    document_filters: Optional[DocumentFilters] = Field(
        None,
        description="Search for specific features or terms within product descriptions. Use for technical requirements",
    )
    sort_by: Optional[Literal["price", "average_rating", "rating_number"]] = Field(
        None,
        description="After finding relevant products, sort them by what matters most. Default: relevance only",
    )
    sort_order: Literal["asc", "desc"] = Field(
        "desc",
        description="Sort direction. 'asc' = lowest first (good for price), 'desc' = highest first (good for ratings)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "Simple search - let relevance do the work",
                    "value": {
                        "query": "wireless headphones for music and calls",
                        "limit": 10,
                    },
                },
                {
                    "description": "Budget-conscious search with quality focus",
                    "value": {
                        "query": "comfortable over-ear headphones for long listening sessions",
                        "limit": 10,
                        "filters": {
                            "max_price": 100.0,
                            "min_rating": 4.0,
                        },
                        "sort_by": "price",
                        "sort_order": "asc",
                    },
                },
                {
                    "description": "Premium search with specific requirements",
                    "value": {
                        "query": "professional studio headphones for music production",
                        "limit": 15,
                        "filters": {
                            "min_price": 200.0,
                            "min_rating": 4.5,
                        },
                        "document_filters": {
                            "contains": ["studio", "professional"],
                            "contains_any": [
                                "Audio-Technica",
                                "Sennheiser",
                                "Beyerdynamic",
                                "AKG",
                            ],
                            "not_contains": ["gaming", "bluetooth"],
                        },
                        "sort_by": "average_rating",
                        "sort_order": "desc",
                    },
                },
                {
                    "description": "Feature-specific search",
                    "value": {
                        "query": "waterproof wireless earbuds for running",
                        "limit": 10,
                        "document_filters": {
                            "contains": ["waterproof", "wireless"],
                            "contains_any": ["IPX7", "IPX8", "IP67", "IP68"],
                        },
                        "filters": {
                            "min_rating": 4.0,
                        },
                    },
                },
            ]
        }
    )

    @field_validator("query", mode="before")
    def clean_query(cls, v):
        """Clean and validate search query."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Query cannot be empty or just whitespace")
        return cleaned


# -------------------------------------------------------------------------
# RESPONSE MODELS
# -------------------------------------------------------------------------


class ProductResponse(BaseModel):
    """
    Complete product search results with all available information.

    This format includes everything about each product. Use ProductResponseLLM
    instead for user-facing responses to keep things concise.
    """

    products: List[ProductItem] = Field(
        ...,
        description="Complete product information for all matching items",
    )
    count: int = Field(
        ...,
        ge=0,
        description="Total number of products found",
    )


class ProductResponseLLM(BaseModel):
    """
    User-friendly search results optimized for clear, helpful responses.

    This format provides all the essential information users need to make decisions
    while keeping responses concise and easy to read. Perfect for:
    - Product recommendations
    - Comparison shopping
    - Quick browsing

    Each product includes: name, price, rating, reviews, brand, and relevance score.
    """

    products: List[ProductItemLLM] = Field(
        ...,
        description="Essential product information formatted for easy reading",
    )
    count: int = Field(
        ...,
        ge=0,
        description="How many matching products were found",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Streamlined results that focus on what users care about most"
        }
    )
