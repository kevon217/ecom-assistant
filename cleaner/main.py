"""
Main entry point for data cleaning pipeline.
"""

import logging
import os
from pathlib import Path

import yaml

from cleaner.pipeline import PipelineOrchestrator


def setup_logging():
    """Configure logging with proper format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def safe_symlink(target, link_name):
    target = os.path.abspath(target)
    link_name = os.path.abspath(link_name)
    try:
        if os.path.islink(link_name) or os.path.exists(link_name):
            os.remove(link_name)
        os.symlink(target, link_name)
    except Exception as e:
        print(f"[WARN] Could not symlink {link_name} -> {target}: {e}")


def main():
    """
    Run the data cleaning pipeline for datasets specified in config.yaml.
    """
    setup_logging()
    logger = logging.getLogger("main")

    try:
        # Initialize pipeline
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        datasets_to_process = config.get("datasets_to_process", [])
        if not datasets_to_process:
            logger.error("No datasets specified in datasets_to_process in config.yaml")
            return
        pipeline = PipelineOrchestrator(config_path)
        for dataset in datasets_to_process:
            logger.info(f"Processing {dataset} dataset...")
            pipeline.process_dataset(dataset)
        logger.info("Pipeline completed successfully!")

        # Update symlinks
        safe_symlink(
            "data/processed/latest/orders/orders_cleaned.csv", "data/orders_cleaned.csv"
        )
        safe_symlink(
            "data/processed/latest/products/products_cleaned.csv",
            "data/products_cleaned.csv",
        )
        safe_symlink(
            "data/processed/latest/orders/orders_cleaned.csv",
            "data/processed/latest/orders_cleaned.csv",
        )
        safe_symlink(
            "data/processed/latest/products/products_cleaned.csv",
            "data/processed/latest/products_cleaned.csv",
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
