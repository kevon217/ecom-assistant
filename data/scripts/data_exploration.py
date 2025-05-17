#!/usr/bin/env python3
"""
Exploratory Data Analysis for ecom-assistant project

Generates comprehensive profiling reports for raw datasets to understand:
- Data types and distributions
- Missing values
- Correlations
- Basic statistics
- Potential data quality issues
"""

from datetime import datetime
from typing import Any, Dict

import pandas as pd
from utils import (
    create_run_directories,
    generate_llm_profile,
    get_project_paths,
    load_config,
    load_dataset,
    save_json_output,
    setup_logging,
)
from ydata_profiling import ProfileReport


def create_data_summary(df: pd.DataFrame, name: str) -> Dict[str, Any]:
    """Create a summary of the dataset."""
    return {
        "name": name,
        "total_records": len(df),
        "columns": list(df.columns),
        "memory_usage_mb": df.memory_usage().sum() / 1024**2,
        "missing_values": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }


def main():
    # Load configuration
    config = load_config()
    paths = get_project_paths(config)

    # Set up logging
    logger = setup_logging(paths["logs"], "data_exploration")
    logger.info("Starting data exploration process...")

    # Create run directories
    run_dirs = create_run_directories(
        paths["analysis"], "eda", ["metrics", "profiles", "llm"]
    )
    logger.info(f"Created run directories at {run_dirs['metrics'].parent}")

    # Load datasets
    logger.info("Loading datasets...")
    orders_raw = load_dataset(config, "orders", paths)
    products_raw = load_dataset(config, "products", paths)

    # Generate full profiles
    logger.info("Generating full product data profile...")
    product_profile = ProfileReport(
        products_raw,
        title=f"Raw Product Data Analysis - {run_dirs['metrics'].parent.name}",
        explorative=True,
        minimal=False,
    )
    product_profile.to_file(run_dirs["profiles"] / "product_report.html")
    product_profile.to_file(run_dirs["profiles"] / "product_report.json")

    logger.info("Generating full order data profile...")
    order_profile = ProfileReport(
        orders_raw,
        title=f"Raw Order Data Analysis - {run_dirs['metrics'].parent.name}",
        explorative=True,
        minimal=False,
    )
    order_profile.to_file(run_dirs["profiles"] / "order_report.html")
    order_profile.to_file(run_dirs["profiles"] / "order_report.json")

    # Generate LLM-optimized profiles
    logger.info("Generating LLM-optimized profiles...")
    generate_llm_profile(
        products_raw,
        f"raw_product_data_{run_dirs['metrics'].parent.name}",
        run_dirs["llm"],
        logger,
    )
    generate_llm_profile(
        orders_raw,
        f"raw_order_data_{run_dirs['metrics'].parent.name}",
        run_dirs["llm"],
        logger,
    )

    # Create data summaries
    summaries = {
        "orders": create_data_summary(orders_raw, "Order Data"),
        "products": create_data_summary(products_raw, "Product Data"),
        "timestamp": datetime.now().isoformat(),
    }
    save_json_output(summaries, run_dirs["metrics"] / "raw_data_summary.json")

    logger.info("\n✅ EDA complete:")
    logger.info(f"  - All outputs saved to: {run_dirs['metrics'].parent}")
    logger.info(f"  - Full profiles saved to: {run_dirs['profiles']}")
    logger.info(f"  - LLM-optimized files saved to: {run_dirs['llm']}")
    logger.info("\nKey Metrics:")
    logger.info(f"  Orders: {summaries['orders']['total_records']} records")
    logger.info(f"  Products: {summaries['products']['total_records']} records")
    logger.info(f"  Order data size: {summaries['orders']['memory_usage_mb']:.2f} MB")
    logger.info(
        f"  Product data size: {summaries['products']['memory_usage_mb']:.2f} MB"
    )


if __name__ == "__main__":
    main()
