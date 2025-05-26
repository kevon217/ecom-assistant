# Data Directory

This directory contains all initial data and analysis outputs for the ecom-assistant project. See cleaner/ for more recent pipeline details.

## Directory Structure

```
data/
├── raw/                           # Original, unmodified datasets
│   ├── Product_Information_Dataset.csv
│   └── Order_Data_Dataset.csv
│
├── processed/                     # Cleaned and transformed data
│   ├── YYYYMMDD_HHMM/            # Timestamped versions
│   │   ├── csv/                  # Human-readable format
│   │   │   ├── orders_clean_*.csv
│   │   │   └── products_clean_*.csv
│   │   └── parquet/              # Optimized for analysis
│   │       ├── orders_processed_*.parquet
│   │       └── products_processed_*.parquet
│   └── latest/                   # Symlinks to most recent versions
│       ├── orders_clean.csv      -> ../YYYYMMDD_HHMM/csv/orders_clean_*.csv
│       ├── products_clean.csv    -> ../YYYYMMDD_HHMM/csv/products_clean_*.csv
│       ├── orders_processed.parquet  -> ../YYYYMMDD_HHMM/parquet/orders_processed_*.parquet
│       └── products_processed.parquet -> ../YYYYMMDD_HHMM/parquet/products_processed_*.parquet
│
├── analysis/                     # Analysis outputs
│   ├── eda/                     # Exploratory Data Analysis
│   │   └── YYYYMMDD_HHMM/      # Timestamped EDA runs
│   │       ├── metrics/        # Data quality metrics
│   │       │   └── raw_data_summary.json  # Dataset statistics
│   │       ├── profiles/       # Detailed data profiles
│   │       │   ├── order_report.html   # Interactive visualizations
│   │       │   ├── order_report.json   # Full profile data
│   │       │   ├── product_report.html
│   │       │   └── product_report.json
│   │       └── llm/           # AI-optimized outputs
│   │           ├── raw_order_data_*.json    # Concise profiles
│   │           └── raw_product_data_*.json
│   │
│   └── cleaning/               # Data Cleaning Analysis
│       └── YYYYMMDD_HHMM/     # Timestamped cleaning runs
│           ├── metrics/       # Quality metrics
│           │   └── quality_metrics.json  # Detailed quality stats
│           ├── comparisons/   # Before/after analysis
│           │   └── comparison_summary.json  # Changes made
│           ├── profiles/      # Cleaned data profiles
│           │   ├── orders_cleaned_full.html
│           │   └── products_cleaned_full.html
│           └── llm/          # AI-optimized outputs
│               ├── cleaned_orders_*.json     # Post-cleaning profiles
│               └── cleaned_products_*.json
│
└── scripts/                    # Data processing scripts
    ├── data_exploration.py     # EDA script (Step 1)
    ├── data_cleaning.py        # Cleaning pipeline (Step 2)
    ├── utils.py               # Shared utilities
    └── config.yaml            # Configuration
```

## Usage Guidelines

1. **Raw Data**
   - Never modify files in `raw/` directly
   - All raw data should be treated as immutable
   - New data sources should be added here first

2. **Data Processing Workflow**

   Step 1: **Exploratory Data Analysis**
   - Run `data/scripts/data_exploration.py` first
   - Generates comprehensive analysis of raw data:
     - Data distributions and patterns (`profiles/*.html`)
     - Missing value analysis (`metrics/raw_data_summary.json`)
     - Data quality metrics (`metrics/quality_metrics.json`)
     - LLM-optimized profiles (`llm/*.json`) for quick insights
   - Use these insights to inform cleaning strategy

   Step 2: **Data Cleaning**
   - After understanding the data, run `data/scripts/data_cleaning.py`
   - Applies standardization and cleaning based on EDA insights
   - Outputs:
     - Cleaned parquet files in `processed/YYYYMMDD_HHMM/`
     - Before/after comparison reports (`comparisons/comparison_summary.json`)
     - Quality metrics tracking improvements
   - Latest versions always available in `processed/latest/`

3. **Analysis Outputs**
   - Each script run creates a timestamped directory containing:
     - HTML reports for interactive exploration
     - JSON metrics for programmatic analysis
     - LLM-optimized profiles for AI integration
   - EDA outputs help identify data issues
   - Cleaning outputs track improvements and changes made

4. **Scripts**
   - Configuration in `config.yaml`
   - Shared utilities in `utils.py`
   - Run scripts from project root directory
   - All paths are resolved relative to `data/` directory
