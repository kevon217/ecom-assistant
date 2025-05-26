# Data Cleaning Pipeline

A robust data cleaning and analysis pipeline for e-commerce datasets. This pipeline handles data validation, cleaning, profiling, and structured output generation for both order and product data.

## Directory Structure

```
cleaner/
├── pipeline.py         # Main pipeline orchestrator
├── data_cleaner.py    # Core data cleaning logic
├── storage_manager.py  # Output file and embedding management
├── schema.py          # Data schemas and validation
├── config.yaml        # Pipeline configuration
├── main.py           # CLI entry point
└── tests/            # Test suite
```

## Features

- **Configurable Data Cleaning**: Field-specific cleaning rules defined in `config.yaml`
- **Automated Profiling**: ydata-profiling reports for both raw and cleaned data
- **Versioned Outputs**: Timestamped runs with latest/ symlinks
- **Structured Analysis**: Separate analysis outputs from cleaned data
- **Vector Store Integration**: Optional embedding generation and upsert

## Output Structure

```
data/
├── raw/              # Source data files
└── processed/
    ├── runs/         # Timestamped run outputs
    │   └── {run_id}/
    │       ├── orders/
    │       └── products/
    ├── latest/      # Symlinks to most recent run
    └── analysis/
        └── profiles/ # ydata profiling reports
```

## Usage

1. **Basic Run**:

   ```bash
   cd cleaner
   python pipeline.py config.yaml
   ```

2. **Configuration**:
   - Edit `config.yaml` to customize:
     - Field processing rules
     - Data paths
     - Analysis settings
     - Profiling options

3. **Outputs**:
   - Cleaned CSVs: `data/processed/latest/{dataset}/{dataset}_cleaned.csv`
   - Profiles: `data/processed/analysis/profiles/{run_id}/{dataset}/`
   - Run data: `data/processed/runs/{run_id}/{dataset}/`

## Data Processing

### Orders Dataset

- Datetime normalization with UTC timezone
- Missing value handling for numeric fields
- Customer ID validation
- Order timestamp generation

### Products Dataset

- Text cleaning (lowercase, special chars)
- Structured field parsing (features, descriptions)
- Category normalization
- Metadata preservation

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
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Testing**:

   ```bash
   # Run test suite
   pytest tests/
   ```

3. **Adding New Features**:
   - Add field processors in `data_cleaner.py`
   - Update schemas in `schema.py`
   - Add configuration in `config.yaml`
   - Add corresponding tests

## Error Handling

The pipeline handles various error cases:

- Missing input files
- Invalid field configurations
- Data type mismatches
- Profile generation failures
- Storage/filesystem issues

Errors are logged with appropriate context and the pipeline continues processing where possible.

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
