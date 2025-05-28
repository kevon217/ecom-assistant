# Data Cleaning Pipeline

Data cleaning and analysis pipeline for e-commerce datasets. Processes order and product data with validation, cleaning, profiling, and structured output generation.

## Directory Structure

```
cleaner/
├── main.py             # CLI entry point
├── pipeline.py         # Pipeline orchestrator
├── data_cleaner.py     # Core data cleaning logic
├── model_validators.py # Data validation models
├── schema.py           # Data schemas and validation
├── utils.py            # Utility functions
├── config.yaml         # Pipeline configuration
└── tests/              # Test suite
    ├── test_cleaning.py
    └── __init__.py
```

## Features

- Field-specific cleaning rules defined in `config.yaml`
- Data profiling reports for raw and cleaned data using ydata-profiling
- Timestamped runs with latest/ symlinks for versioned outputs
- Separate analysis outputs from cleaned data
- Data validation with Pydantic models

## Output Structure

```
data/
├── raw/                        # Source CSV files
├── processed/
│   ├── runs/                   # Timestamped run outputs
│   │   └── {timestamp}/
│   │       ├── orders/         # Cleaned order data and validation reports
│   │       └── products/       # Cleaned product data and validation reports
│   ├── latest/                 # Symlinks to most recent run
│   └── analysis/
│       └── profiles/           # ydata-profiling HTML reports
│           └── {timestamp}/
│               ├── orders/
│               └── products/
├── analysis/                   # Legacy analysis outputs
├── chroma/                     # ChromaDB vector store data
├── orders_cleaned.csv          # Symlink to latest cleaned orders
└── products_cleaned.csv        # Symlink to latest cleaned products
```

## Usage

1. **Basic Run**:

   ```bash
   cd cleaner
   python main.py
   ```

2. **Configuration**:
   - Edit `config.yaml` to customize:
     - Field processing rules
     - Data paths
     - Analysis settings
     - Profiling options

3. **Outputs**:
   - Cleaned CSVs: `data/processed/latest/{dataset}_cleaned.csv`
   - Profiles: `data/processed/analysis/profiles/{timestamp}/{dataset}/`
   - Run data: `data/processed/runs/{timestamp}/{dataset}/`

## Data Processing

### Orders Dataset

- Datetime normalization with UTC timezone handling
- Missing value handling for numeric fields
- Customer ID validation and cleaning
- Order timestamp generation from date fields

### Products Dataset

- Text cleaning and normalization
- Structured field parsing for features and descriptions
- Category normalization and validation
- Price and rating data validation

## Configuration

Example `config.yaml` for field processing:

```yaml
datasets:
  orders:
    file: "Order_Data_Dataset.csv"
    fields:
      Order_Date:
        type: "datetime"
        options:
          format: "%Y-%m-%d"
      Sales:
        type: "numeric"
      Customer_Id:
        type: "categorical"
        options:
          drop_duplicates: true
```

## Development

1. **Setup**:

   ```bash
   # Install dependencies with uv
   uv sync

   # Or with pip (if requirements.txt available)
   pip install pandas pydantic pyyaml ydata-profiling
   ```

2. **Testing**:

   ```bash
   # Run test suite
   pytest tests/
   ```

3. **Adding New Features**:
   - Add field processors in `data_cleaner.py`
   - Update validation models in `model_validators.py`
   - Update schemas in `schema.py`
   - Add configuration in `config.yaml`
   - Add corresponding tests

## Error Handling

Pipeline handles common error cases:

- Missing input files
- Invalid field configurations
- Data type mismatches
- Profile generation failures
- Storage/filesystem issues

Errors are logged and the pipeline continues processing where possible.

## Monitoring

- Progress logging with dataset statistics
- Data quality metrics in profiles
- Error tracking and reporting
- Run timestamps and versioning

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update configuration documentation
4. Use type hints and docstrings
5. Follow PEP 8 style guidelines

## Dependencies

- pandas: Data processing
- ydata-profiling: Data analysis
- pydantic: Configuration and validation
- PyYAML: Configuration parsing
