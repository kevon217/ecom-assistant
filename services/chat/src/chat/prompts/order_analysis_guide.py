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
