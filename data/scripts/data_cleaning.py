#!/usr/bin/env python3
"""
Data Cleaning Script for ecom-assistant project

Handles basic data standardization:
- DateTime coercion
- Type standardization
- Text field analysis
- Price standardization
- Data quality metrics
"""

import ast
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from utils import (
    create_run_directories,
    generate_llm_profile,
    get_dataset_fields,
    get_project_paths,
    load_config,
    load_dataset,
    save_json_output,
    setup_logging,
)
from ydata_profiling import ProfileReport


def standardize_datetime(
    df: pd.DataFrame, datetime_fields: Dict[str, List[str]], logger: logging.Logger
) -> pd.DataFrame:
    """Standardize datetime fields in dataframe."""
    result_df = df.copy()

    # Keep original columns as strings for comparison
    for date_field in datetime_fields.get("date", []):
        if date_field in result_df.columns:
            logger.debug(f"Processing date field: {date_field}")
            result_df[f"{date_field}_raw"] = result_df[date_field]
            result_df[date_field] = pd.to_datetime(result_df[date_field])
            logger.debug(f"Converted {date_field} to datetime")

    for time_field in datetime_fields.get("time", []):
        if time_field in result_df.columns:
            logger.debug(f"Processing time field: {time_field}")
            result_df[f"{time_field}_raw"] = result_df[time_field]

    # Create combined datetime if we have both date and time fields
    if datetime_fields.get("date") and datetime_fields.get("time"):
        date_field = datetime_fields["date"][0]
        time_field = datetime_fields["time"][0]
        if date_field in result_df.columns and time_field in result_df.columns:
            logger.debug(
                f"Creating combined datetime from {date_field} and {time_field}"
            )
            result_df["datetime"] = pd.to_datetime(
                result_df[date_field].astype(str)
                + " "
                + result_df[time_field].astype(str)
            )

    return result_df


def standardize_numeric(
    df: pd.DataFrame, numeric_fields: List[str], logger: logging.Logger
) -> pd.DataFrame:
    """Standardize numeric fields in dataframe."""
    result_df = df.copy()

    for field in numeric_fields:
        if field not in result_df.columns:
            logger.warning(f"Numeric field {field} not found in dataframe")
            continue

        logger.debug(f"Processing numeric field: {field}")
        # Convert 'None' strings to pd.NA
        result_df[field] = result_df[field].replace("None", pd.NA)
        # Ensure numeric type
        result_df[field] = pd.to_numeric(result_df[field], errors="coerce")
        logger.debug(f"Converted {field} to numeric type")

    return result_df


def standardize_list_fields(
    df: pd.DataFrame, list_fields: List[str], logger: logging.Logger
) -> pd.DataFrame:
    """Standardize list fields in dataframe."""
    result_df = df.copy()

    for field in list_fields:
        if field not in result_df.columns:
            logger.warning(f"List field {field} not found in dataframe")
            continue

        logger.debug(f"Processing list field: {field}")
        # Keep original as raw
        result_df[f"{field}_raw"] = result_df[field]

        def parse_list(value):
            if pd.isna(value):
                return []
            try:
                if isinstance(value, str):
                    parsed = ast.literal_eval(value)
                    return parsed if isinstance(parsed, list) else []
                return [] if value is None else list(value)
            except (ValueError, SyntaxError):
                return []

        # Convert to proper lists and clean empty strings
        result_df[field] = result_df[field].apply(parse_list)

        # Clean empty strings and strip whitespace
        result_df[field] = result_df[field].apply(
            lambda lst: [str(item).strip() for item in lst if str(item).strip()]
        )

        logger.debug(f"Standardized {field} list field")

    return result_df


def create_processed_directories(base_path: Path, timestamp: str) -> Dict[str, Path]:
    """Create timestamped directories for processed data outputs.

    Args:
        base_path: Base processed data directory
        timestamp: Timestamp string (YYYYMMDD_HHMM)

    Returns:
        Dictionary of paths for different output types
    """
    run_dir = base_path / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    return {"base": run_dir, "csv": run_dir / "csv", "parquet": run_dir / "parquet"}


def create_comparison_report(
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    dataset_name: str,
    output_dir: Path,
    logger: logging.Logger,
) -> None:
    """Create a comparison report between raw and cleaned data."""
    logger.info(f"Creating comparison report for {dataset_name}...")

    # Track new and modified columns
    new_columns = [col for col in cleaned_df.columns if col not in raw_df.columns]
    common_columns = [col for col in raw_df.columns if col in cleaned_df.columns]

    # Track type changes
    type_changes = {
        col: {"from": str(raw_df[col].dtype), "to": str(cleaned_df[col].dtype)}
        for col in common_columns
        if raw_df[col].dtype != cleaned_df[col].dtype
    }

    # Track missing values per column
    missing_values = {
        col: {
            "before": int(raw_df[col].isnull().sum()),
            "after": int(cleaned_df[col].isnull().sum()),
            "difference": int(
                cleaned_df[col].isnull().sum() - raw_df[col].isnull().sum()
            ),
        }
        for col in common_columns
    }

    # Special handling for list fields if present
    list_field_changes = {}
    for col in common_columns:
        if col.endswith("_raw"):  # Skip raw backup columns
            continue
        # Check if column contains list-like data
        if cleaned_df[col].dtype == "object" and cleaned_df[col].notna().any():
            sample = cleaned_df[col].iloc[0]
            if isinstance(sample, list):
                # Analyze list content changes
                list_field_changes[col] = {
                    "empty_lists": {
                        "before": int(
                            raw_df[col]
                            .apply(
                                lambda x: str(x).strip() in ["[]", "", "None", "nan"]
                            )
                            .sum()
                        ),
                        "after": int(
                            cleaned_df[col]
                            .apply(lambda x: not x if isinstance(x, list) else True)
                            .sum()
                        ),
                    },
                    "avg_length": {
                        "before": float(
                            raw_df[col]
                            .apply(
                                lambda x: len(eval(str(x)))
                                if pd.notna(x)
                                and str(x).strip() not in ["", "None", "nan"]
                                else 0
                            )
                            .mean()
                        ),
                        "after": float(
                            cleaned_df[col]
                            .apply(lambda x: len(x) if isinstance(x, list) else 0)
                            .mean()
                        ),
                    },
                }

    comparison = {
        "column_changes": {"new_columns": new_columns, "type_changes": type_changes},
        "row_count": {
            "before": int(len(raw_df)),
            "after": int(len(cleaned_df)),
            "difference": int(len(cleaned_df) - len(raw_df)),
        },
        "missing_values": {
            "total": {
                "before": int(raw_df.isnull().sum().sum()),
                "after": int(cleaned_df.isnull().sum().sum()),
                "difference": int(
                    cleaned_df.isnull().sum().sum() - raw_df.isnull().sum().sum()
                ),
            },
            "by_column": missing_values,
        },
    }

    # Add list field changes if any were found
    if list_field_changes:
        comparison["list_fields"] = list_field_changes

    # Save comparison report
    output_path = output_dir / "comparison_summary.json"
    if not output_path.exists():
        comparison_data = {}
    else:
        with open(output_path) as f:
            comparison_data = json.load(f)

    comparison_data[dataset_name] = comparison
    save_json_output(comparison_data, output_path)

    logger.info(f"Saved comparison report to {output_path}")


def generate_cleaned_profiles(
    df: pd.DataFrame,
    dataset_name: str,
    output_dir: Path,
    logger: logging.Logger,
) -> None:
    """Generate profiles for cleaned data."""
    logger.info(f"Generating cleaned data profile for {dataset_name}...")

    # Generate full profile
    profile = ProfileReport(
        df,
        title=f"Cleaned {dataset_name} Analysis",
        explorative=True,
        minimal=False,
    )

    # Save HTML and JSON versions
    profile.to_file(output_dir / f"{dataset_name.lower()}_cleaned_full.html")
    profile.to_file(output_dir / f"{dataset_name.lower()}_cleaned_full.json")

    # Generate LLM-optimized profile
    generate_llm_profile(
        df, f"cleaned_{dataset_name.lower()}", output_dir.parent / "llm", logger
    )


def generate_quality_metrics(
    df: pd.DataFrame,
    dataset_name: str,
    output_dir: Path,
    logger: logging.Logger,
) -> Dict[str, Any]:
    """Generate quality metrics for cleaned data."""
    logger.info(f"Generating quality metrics for {dataset_name}...")

    metrics = {
        "dataset": dataset_name,
        "timestamp": datetime.now().isoformat(),
        "row_count": len(df),
        "column_count": len(df.columns),
        "memory_usage_mb": df.memory_usage().sum() / 1024**2,
        "missing_values": {
            "total": int(df.isnull().sum().sum()),
            "by_column": df.isnull().sum().to_dict(),
        },
        "dtypes": df.dtypes.astype(str).to_dict(),
    }

    # Save metrics
    metrics_file = output_dir / "quality_metrics.json"
    if not metrics_file.exists():
        all_metrics = {}
    else:
        with open(metrics_file) as f:
            all_metrics = json.load(f)

    all_metrics[dataset_name] = metrics
    save_json_output(all_metrics, metrics_file)

    return metrics


def main():
    # Load configuration
    config = load_config()
    paths = get_project_paths(config)

    # Set up logging
    logger = setup_logging(paths["logs"], "data_cleaning")
    logger.info("Starting data cleaning process...")

    # Create timestamped directories
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    run_dirs = create_run_directories(
        paths["analysis"], "cleaning", ["metrics", "profiles", "comparisons", "llm"]
    )
    processed_dirs = create_processed_directories(paths["processed"], timestamp)

    for dir_path in processed_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created run directories at {run_dirs['metrics'].parent}")
    logger.info(f"Created processed data directories at {processed_dirs['base']}")

    # Load datasets
    logger.info("Loading datasets...")
    orders_raw = load_dataset(config, "orders", paths)
    products_raw = load_dataset(config, "products", paths)

    # Get field configurations
    orders_fields = get_dataset_fields(config, "orders")
    products_fields = get_dataset_fields(config, "products")

    # Process orders
    logger.info("Processing orders data...")
    orders_cleaned = standardize_datetime(
        orders_raw, orders_fields.get("datetime", {}), logger
    )
    orders_cleaned = standardize_numeric(
        orders_cleaned, orders_fields.get("numeric", {}), logger
    )

    # Process products
    logger.info("Processing products data...")
    products_cleaned = standardize_numeric(
        products_raw, products_fields.get("numeric", {}), logger
    )
    products_cleaned = standardize_list_fields(
        products_cleaned, products_fields.get("list", {}), logger
    )

    # Create comparison reports
    create_comparison_report(
        orders_raw, orders_cleaned, "orders", run_dirs["comparisons"], logger
    )
    create_comparison_report(
        products_raw, products_cleaned, "products", run_dirs["comparisons"], logger
    )

    # Generate profiles and metrics for cleaned data
    logger.info("Generating profiles and metrics for cleaned data...")

    # Orders
    generate_cleaned_profiles(orders_cleaned, "Orders", run_dirs["profiles"], logger)
    generate_quality_metrics(orders_cleaned, "orders", run_dirs["metrics"], logger)

    # Products
    generate_cleaned_profiles(
        products_cleaned, "Products", run_dirs["profiles"], logger
    )
    generate_quality_metrics(products_cleaned, "products", run_dirs["metrics"], logger)

    # Save processed data with timestamps
    logger.info("Saving processed datasets...")
    orders_csv_path = processed_dirs["csv"] / f"orders_clean_{timestamp}.csv"
    products_csv_path = processed_dirs["csv"] / f"products_clean_{timestamp}.csv"
    orders_parquet_path = (
        processed_dirs["parquet"] / f"orders_processed_{timestamp}.parquet"
    )
    products_parquet_path = (
        processed_dirs["parquet"] / f"products_processed_{timestamp}.parquet"
    )

    # Save CSV versions
    orders_cleaned.to_csv(orders_csv_path, index=False)
    products_cleaned.to_csv(products_csv_path, index=False)

    # Save Parquet versions
    orders_cleaned.to_parquet(orders_parquet_path, index=False)
    products_cleaned.to_parquet(products_parquet_path, index=False)

    logger.info(f"Saved processed data to {processed_dirs['base']}")

    # Create symlinks to latest versions
    latest_dir = paths["processed"] / "latest"
    latest_dir.mkdir(exist_ok=True)

    for file_path in [
        orders_csv_path,
        products_csv_path,
        orders_parquet_path,
        products_parquet_path,
    ]:
        latest_link = latest_dir / file_path.name.replace(f"_{timestamp}", "")
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(file_path)

    logger.info(f"Updated latest symlinks in {latest_dir}")


if __name__ == "__main__":
    main()
