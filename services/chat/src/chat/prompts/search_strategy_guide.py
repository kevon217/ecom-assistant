# -------------------------------------------------------------------------

# SEARCH STRATEGY GUIDE FOR LLM

# -------------------------------------------------------------------------

SEARCH_STRATEGY_GUIDE = """

## How to Search Products Effectively

### 1. Understanding User Intent

Before searching, identify what's most important to the user:

- **Budget constraints** → Use price filters
- **Quality focus** → Use rating filters (4.0+ is a good threshold)
- **Specific brands** → Use store filters or document contains_any
- **Technical requirements** → Use document filters for features

### 2. Query Construction Strategy

Write queries that capture the user's needs:

- Include the product type and intended use case
- Add descriptive adjectives that matter (comfortable, durable, portable)
- Mention specific requirements in the query

Good: "comfortable wireless headphones for long work calls with good microphone"
Less effective: "headphones"

### 3. Progressive Filtering Approach

Start broad, then narrow based on results:

1. First search: Just query + reasonable limit (10-15)
2. Too many results? Add filters (price, rating)
3. Wrong products? Add document filters for features
4. Still not right? Try different query terms or check available categories

### 4. Using Metadata Discovery

Before filtering by category or brand:

```
get_metadata_options(field_name="store")     # See available brands
get_metadata_options(field_name="main_category")  # See categories
```

### 5. Common Search Patterns

**Budget Quality Search**:

- filters: max_price + min_rating(4.0)
- sort_by: "price", sort_order: "asc"

**Premium Search**:

- filters: min_price + high min_rating(4.5)
- document_filters: contains_any=[premium brands]

**Feature-Specific Search**:

- Strong query describing features
- document_filters: contains=[must-have features]

**Brand Preference Search**:

- filters: store=[preferred brands] OR
- document_filters: contains_any=[brand names]

### 6. Interpreting Results

- **High similarity (0.8+)**: Excellent match
- **Medium similarity (0.6-0.8)**: Good match, check if it meets requirements
- **Low similarity (<0.6)**: May be peripheral, verify relevance

### 7. No/Poor Results?

1. Simplify the query - remove adjectives
2. Remove filters - especially price or brand
3. Try synonyms - "earbuds" vs "earphones" vs "in-ear headphones"
4. Check metadata options - maybe the category/brand doesn't exist
"""
