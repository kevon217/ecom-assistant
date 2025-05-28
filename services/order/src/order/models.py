# services/order/src/order/models.py
"""
Order service models designed to help you analyze customer behavior and business metrics.
Use these tools to understand orders, customers, and sales patterns.
"""

from typing import Any, Dict, List, Literal, Optional

from libs.ecom_shared.models import PaginatedResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OrderItem(BaseModel):
    """
    Complete order information with customer and product details.

    Each order represents a transaction between a customer and your business.
    Use this data to understand purchasing patterns, customer behavior, and business performance.
    """

    # Core identifiers
    order_id: str = Field(
        ...,
        description="System-generated unique order identifier",
        exclude=True,  # Hide from LLM
    )
    customer_id: int = Field(
        ...,
        description="5-digit customer identifier - use to analyze customer behavior",
        example=12345,
    )

    # Product information
    product_category: str = Field(
        ...,
        description="Main category: Fashion (50%), Home & Furniture (30%), Auto & Accessories (15%), Electronic (5%)",
        example="Home & Furniture",
    )
    product: Optional[str] = Field(
        None, description="Specific product type within category", example="Towels"
    )

    # Financial metrics
    sales: float = Field(
        ...,
        ge=0,
        description="Total sale amount in USD",
        example=299.99,
    )
    profit: float = Field(
        ...,
        description="Profit generated from this order",
        example=45.50,
    )
    shipping_cost: float = Field(
        ...,
        ge=0,
        description="Cost to ship this order",
        example=12.99,
    )
    discount: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Discount percentage applied (0.0 to 1.0, where 0.2 = 20% off)",
        example=0.15,
    )

    # Order details
    quantity: Optional[float] = Field(
        None, ge=0, description="Number of items ordered", example=2.0
    )
    order_priority: str = Field(
        ...,
        description="Urgency level: Medium (57%), High (30%), Critical (8%), Low (5%)",
        example="Medium",
    )
    order_date: str = Field(
        ...,
        description="Date when order was placed (YYYY-MM-DD format)",
        example="2018-06-25",
    )

    # Customer demographics
    gender: Optional[str] = Field(
        None,
        description="Customer gender: Male (55%) or Female (45%)",
        example="Female",
    )
    payment_method: Optional[str] = Field(
        None,
        description="How the customer paid - tracks payment preferences",
        example="Credit Card",
    )
    device_type: Optional[str] = Field(
        None,
        description="How order was placed: Web (93%) or Mobile (7%)",
        example="Web",
    )
    customer_login_type: Optional[str] = Field(
        None,
        description="Account type: Member (96%), Guest (4%), First SignUp (<1%), New (<1%)",
        example="Member",
    )

    # Additional metadata
    time: str = Field(
        ...,
        description="Time of day when order was placed (HH:MM:SS)",
        example="21:49:14",
    )
    aging: float = Field(
        ...,
        description="Days elapsed since order was placed (1-10.5 range in data)",
        example=2.0,
    )
    order_timestamp: str = Field(
        ...,
        description="Combined date and time for precise ordering",
        example="2018-06-25 21:49:14",
    )

    # System fields (less relevant for analysis)
    embed_text: Optional[str] = Field(
        None,
        description="Text representation for embedding/search purposes",
        exclude=True,
    )
    embed_checksum: Optional[str] = Field(
        None, description="Checksum for data integrity", exclude=True
    )

    @field_validator("product_category")
    def normalize_category(cls, v):
        """Normalize category names."""
        if v:
            # Handle the 'Electronic' vs 'Electronics' inconsistency
            if v.lower() == "electronic":
                return "Electronics"
        return v

    @field_validator("order_priority")
    def validate_priority(cls, v):
        """Ensure valid priority levels."""
        valid_priorities = ["Critical", "High", "Medium", "Low"]
        if v and v not in valid_priorities:
            # Try to normalize
            normalized = v.strip().title()
            if normalized in valid_priorities:
                return normalized
        return v

    @field_validator("gender")
    def normalize_gender(cls, v):
        """Normalize gender values."""
        if v:
            normalized = v.strip().upper()
            if normalized in ["M", "F", "MALE", "FEMALE", "OTHER"]:
                return normalized[0] if len(normalized) > 1 else normalized
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "order_id": "69284798-c50c-46fc-b625-decab0e5ef72",
                "customer_id": 12345,
                "product_category": "Technology",
                "product": "Wireless Bluetooth Headphones",
                "sales": 149.99,
                "profit": 32.50,
                "shipping_cost": 9.99,
                "order_priority": "High",
                "gender": "F",
                "payment_method": "Credit Card",
                "order_date": "2024-03-15",
                "quantity": 1.0,
                "device_type": "Mobile",
            }
        },
    )


class OrderSearchRequest(BaseModel):
    """
    Flexible order search with filtering and sorting capabilities.

    Use this to find orders matching specific criteria. You can filter by any field
    and sort results to highlight what matters most.

    Filter examples:
    - By category: {"product_category": "Technology"}
    - By priority: {"order_priority": "High"}
    - By profit range: {"profit": {"$gt": 100}}
    - By date: {"order_date": {"$gt": "2024-01-01"}}

    Combine multiple filters for precise searches.
    """

    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filter orders by any field. Use exact matches or operators like $gt (greater than), $lt (less than), $contains",
        example={"product_category": "Technology", "profit": {"$gt": 50}},
    )

    sort: Optional[Literal["sales", "profit", "shipping_cost", "order_date"]] = Field(
        None,
        description="Sort results by this field (descending). Choose what matters most for your analysis",
        example="profit",
    )

    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of results (1-100). Use smaller limits for quick overviews, larger for comprehensive analysis",
        example=20,
    )

    @field_validator("filters")
    def validate_filters(cls, v):
        """Ensure filters are properly structured."""
        if v:
            # Basic validation - could be expanded
            if not isinstance(v, dict):
                raise ValueError("Filters must be a dictionary")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "High-value technology orders",
                    "value": {
                        "filters": {
                            "product_category": "Technology",
                            "sales": {"$gt": 500},
                        },
                        "sort": "profit",
                        "limit": 10,
                    },
                },
                {
                    "title": "Recent critical orders",
                    "value": {
                        "filters": {
                            "order_priority": "Critical",
                            "order_date": {"$gt": "2024-01-01"},
                        },
                        "sort": "order_date",
                        "limit": 20,
                    },
                },
                {
                    "title": "Loss-making orders analysis",
                    "value": {
                        "filters": {"profit": {"$lt": 0}},
                        "sort": "profit",
                        "limit": 15,
                    },
                },
            ]
        }
    )


class OrdersResponse(PaginatedResponse[OrderItem]):
    """
    Paginated response containing order search results.

    Provides both the requested orders and metadata about the results,
    helping you understand the scope of your query.
    """

    returned_count: int = Field(
        ...,
        ge=0,
        description="How many orders are included in this response",
        example=10,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Order results with pagination metadata for large datasets"
        }
    )


class CustomerStats(BaseModel):
    """
    Comprehensive statistics about a customer's ordering behavior.

    This aggregated view helps you understand customer value, preferences,
    and engagement patterns - perfect for personalized recommendations or analysis.
    """

    customer_id: int = Field(
        ..., description="The customer these statistics describe", example=12345
    )

    # Order metrics
    total_orders: int = Field(
        ..., ge=0, description="How many orders this customer has placed", example=47
    )
    total_spent: float = Field(
        ...,
        ge=0,
        description="Total amount customer has spent (revenue)",
        example=3499.85,
    )
    total_profit: float = Field(
        ..., description="Total profit generated from this customer", example=523.45
    )
    average_order_value: float = Field(
        ...,
        ge=0,
        description="Average amount per order - indicates purchasing power",
        example=74.46,
    )

    # Preferences
    favorite_category: Optional[str] = Field(
        None, description="Category this customer buys most often", example="Technology"
    )
    preferred_device: Optional[str] = Field(
        None, description="Device they typically use for ordering", example="Mobile"
    )

    # Order patterns
    order_priorities: Dict[str, int] = Field(
        ...,
        description="Breakdown of order priorities (Critical/High/Medium/Low counts)",
        example={"High": 20, "Medium": 15, "Low": 10, "Critical": 2},
    )

    # Timeline
    first_order_date: Optional[str] = Field(
        None, description="When they became a customer", example="2022-01-15"
    )
    last_order_date: Optional[str] = Field(
        None,
        description="Most recent order - shows engagement recency",
        example="2024-03-15",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": 12345,
                "total_orders": 47,
                "total_spent": 3499.85,
                "total_profit": 523.45,
                "average_order_value": 74.46,
                "favorite_category": "Technology",
                "preferred_device": "Mobile",
                "order_priorities": {
                    "High": 20,
                    "Medium": 15,
                    "Low": 10,
                    "Critical": 2,
                },
                "first_order_date": "2022-01-15",
                "last_order_date": "2024-03-15",
            }
        }
    )


class CategorySalesStats(BaseModel):
    """
    Sales performance metrics for a product category.

    Use this to identify your best-performing categories and where to focus efforts.
    """

    category: str = Field(
        ..., description="Product category name", example="Technology"
    )
    total_sales: float = Field(
        ..., ge=0, description="Total revenue from this category", example=125430.50
    )
    order_count: int = Field(
        ..., ge=0, description="Number of orders in this category", example=342
    )

    @property
    def average_order_value(self) -> float:
        """Calculate average order value for this category."""
        return self.total_sales / self.order_count if self.order_count > 0 else 0.0


class ShippingCostSummary(BaseModel):
    """
    Statistical summary of shipping costs across all orders.

    Helps you understand shipping cost distribution and identify optimization opportunities.
    """

    average_cost: float = Field(
        ..., ge=0, description="Average shipping cost per order", example=12.45
    )
    min_cost: float = Field(
        ..., ge=0, description="Lowest shipping cost observed", example=0.00
    )
    max_cost: float = Field(
        ..., ge=0, description="Highest shipping cost observed", example=89.99
    )
    total_cost: float = Field(
        ...,
        ge=0,
        description="Total spent on shipping across all orders",
        example=45678.90,
    )


class GenderProfitStats(BaseModel):
    """
    Profit analysis segmented by customer gender.

    Useful for understanding demographic purchasing patterns and profitability.
    """

    gender: str = Field(
        ..., description="Gender category (M/F/Other/Unknown)", example="F"
    )
    total_profit: float = Field(
        ..., description="Total profit from this gender segment", example=23456.78
    )
    order_count: int = Field(
        ..., ge=0, description="Number of orders from this gender segment", example=1234
    )

    @property
    def average_profit_per_order(self) -> float:
        """Calculate average profit per order for this segment."""
        return self.total_profit / self.order_count if self.order_count > 0 else 0.0


# -------------------------------------------------------------------------
# ANALYSIS TIPS FOR LLM
# -------------------------------------------------------------------------

ORDER_ANALYSIS_GUIDE = """
## How to Analyze Orders Effectively

### 1. Customer Analysis
Start with individual customer insights:
- Use get_customer_stats to understand spending patterns
- Look at order frequency and recency
- Identify VIP customers (high total_spent + frequent orders)

### 2. Category Performance
Analyze which products drive your business:
- Use total_sales_by_category to find top categories
- Compare order counts to identify popular vs high-value categories
- Look for seasonal patterns in order_date

### 3. Profitability Analysis
Focus on what makes money:
- Search for high-profit orders to identify successful products
- Find negative profit orders to spot problems
- Calculate profit margins (profit/sales ratio)

### 4. Operational Insights
Optimize business operations:
- Analyze shipping costs by category or customer segment
- Check order_priority distribution for capacity planning
- Study device_type to optimize shopping experience

### 5. Common Analysis Patterns

**Customer Lifetime Value**:
- get_customer_stats for spending history
- Calculate: total_profit / months_since_first_order

**Best Customers**:
- Search with filters: {"profit": {"$gt": 100}}
- Sort by profit or sales

**Problem Orders**:
- Negative profit orders
- High shipping cost relative to sales
- Critical priority with old dates

**Demographic Insights**:
- profit_by_gender for segment analysis
- Device preferences by customer segment
- Payment method distribution

### 6. Key Metrics to Track
- Average Order Value (AOV): total_sales / order_count
- Profit Margin: profit / sales
- Customer Retention: last_order_date analysis
- Category Mix: distribution of orders across categories
"""


ORDER_DATASET_CONTEXT = """
## Order Dataset Overview (2018 E-Commerce Data)

**Scale**: 51,290 orders from 38,997 unique customers

**Product Categories**:
- Fashion: 50% (clothing, shoes, watches)
- Home & Furniture: 30% (towels, sofa covers, umbrellas)
- Auto & Accessories: 15% (car & bike care)
- Electronics: 5% (electronic items)

**Customer Demographics**:
- Gender: Male (55%), Female (45%)
- Account Types: Members (96%), Guests (4%)
- Device Usage: Web (93%), Mobile (7%)

**Order Patterns**:
- Average Order Value: $152
- Average Profit: $70 per order
- Typical Quantity: 2-3 items per order
- Discount Range: 10-50% (average 30%)

**Priority Distribution**:
- Medium: 57% (routine orders)
- High: 30% (priority fulfillment)
- Critical: 8% (urgent/express)
- Low: 5% (flexible delivery)

**Payment Methods**:
- Credit Card: 74% (dominant method)
- Money Order: 19% (traditional buyers)
- E-Wallet: 5% (digital adoption)
- Debit Card: 1% (rare)

**Temporal Patterns**:
- Full year of 2018 data
- Order times span 24 hours
- "Aging" shows 1-10 days since order

This historical dataset is ideal for analyzing:
- Customer purchasing patterns
- Category performance
- Payment preferences
- Device usage trends
- Priority distribution for capacity planning
"""
