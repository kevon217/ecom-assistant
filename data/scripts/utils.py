"""
Utility functions for data processing and analysis.

This module provides common functionality used across data cleaning
and exploration scripts, including:
- Configuration management
- Path handling
- Data type validation
- Common data processing functions
"""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd
import yaml
from ydata_profiling import ProfileReport


def setup_logging(log_dir: Path, script_name: str) -> logging.Logger:
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(message)s")

    # File handler
    file_handler = RotatingFileHandler(
        log_dir / f"{script_name}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_serializable_sample(df: pd.DataFrame, n: int = 10) -> List[Dict[str, Any]]:
    """Convert DataFrame to a sample of serializable records."""
    df_copy = df.copy()
    for col in df_copy.columns:
        # Handle different types of columns
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        elif df_copy[col].dtype == "O":  # Object dtype
            # Convert each value to string, handling special cases
            df_copy[col] = df_copy[col].apply(
                lambda x: x.isoformat()
                if hasattr(x, "isoformat")  # Handle datetime-like objects
                else str(x)
                if x is not None  # Handle other non-null objects
                else None  # Keep None as None
            )

    # Take sample and convert to records
    return df_copy.sample(min(n, len(df_copy))).to_dict(orient="records")


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_project_paths(config: Dict[str, Any]) -> Dict[str, Path]:
    """Get standardized paths for project directories."""
    base_dir = Path(__file__).parent.parent

    return {
        "raw": base_dir / "raw",
        "processed": base_dir / "processed",
        "analysis": base_dir / "analysis",
        "logs": base_dir / "logs",
    }


def create_run_directories(
    base_dir: Path, run_type: str, subdirs: list[str] = None
) -> Dict[str, Path]:
    """Create timestamped run directories for analysis outputs.

    Args:
        base_dir (Path): Base analysis directory
        run_type (str): Type of run ('eda' or 'cleaning')
        subdirs (list[str], optional): List of subdirectories to create.
            If None, creates all supported directories.
            Supported values: ['metrics', 'profiles', 'comparisons', 'llm']

    Returns:
        Dict[str, Path]: Dictionary mapping subdirectory names to their paths
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    run_dir = base_dir / run_type / timestamp

    # Define supported subdirectories
    supported_subdirs = {
        "metrics": run_dir / "metrics",  # Quality metrics and analysis
        "profiles": run_dir / "profiles",  # Data profiles (HTML/JSON)
        "comparisons": run_dir / "comparisons",  # Before/after comparisons
        "llm": run_dir / "llm",  # LLM-optimized outputs
    }

    # If no subdirs specified, use all supported ones
    if subdirs is None:
        subdirs = list(supported_subdirs.keys())

    # Validate requested subdirs
    for subdir in subdirs:
        if subdir not in supported_subdirs:
            raise ValueError(
                f"Unsupported subdirectory: {subdir}. Must be one of {list(supported_subdirs.keys())}"
            )

    # Create only requested subdirectories
    created_dirs = {}
    for subdir in subdirs:
        dir_path = supported_subdirs[subdir]
        dir_path.mkdir(parents=True, exist_ok=True)
        created_dirs[subdir] = dir_path

    return created_dirs


def get_dataset_fields(
    config: Dict[str, Any], dataset_name: str
) -> Dict[str, List[str]]:
    """Get field configurations for a specific dataset."""
    if dataset_name not in config["datasets"]:
        raise ValueError(f"Dataset {dataset_name} not found in configuration")

    return config["datasets"][dataset_name]["fields"]


def load_dataset(
    config: Dict[str, Any], dataset_name: str, paths: Dict[str, Path]
) -> pd.DataFrame:
    """Load a dataset based on configuration."""
    if dataset_name not in config["datasets"]:
        raise ValueError(f"Dataset {dataset_name} not found in configuration")

    file_path = paths["raw"] / config["datasets"][dataset_name]["file"]
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found at {file_path}")

    return pd.read_csv(file_path)


def save_json_output(
    data: Union[Dict, List], output_path: Path, indent: int = 2
) -> None:
    """Save data to JSON file with proper formatting.

    Ensures consistent formatting with:
    - Proper indentation
    - UTF-8 encoding
    - Trailing newline
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
        f.write("\n")  # Add trailing newline


def generate_llm_profile(
    df: pd.DataFrame,
    title: str,
    output_dir: Path,
    logger: logging.Logger | None = None,
) -> None:
    """Generate a minimal JSON profile report optimized for LLM consumption.

    Args:
        df: DataFrame to profile
        title: Title for the profile
        output_dir: Directory to save the profile
        logger: Optional logger instance
    """
    if logger:
        logger.debug(f"Generating LLM profile for {title}")

    profile = ProfileReport(df, title=title, minimal=True, explorative=False)
    profile_json = profile.to_json()
    profile_dict = json.loads(profile_json)

    concise_profile = {
        "analysis": {
            "title": profile_dict["analysis"]["title"],
            "date": profile_dict["analysis"]["date_start"],
        },
        "table": {
            "n_rows": profile_dict["table"]["n"],
            "n_columns": profile_dict["table"]["n_var"],
            "n_cells_missing": profile_dict["table"].get("n_cells_missing", 0),
            "p_cells_missing": profile_dict["table"].get("p_cells_missing", 0),
            "column_types": profile_dict["table"].get("types", {}),
            "memory_size": profile_dict["table"].get("memory_size", ""),
        },
        "variables": {},
        "sample_rows": get_serializable_sample(df),
    }

    # Process each variable
    for var_name, var_data in profile_dict["variables"].items():
        var_type = var_data["type"]
        var_metrics = {
            "type": var_type,
            "n_missing": var_data.get("n_missing", 0),
            "p_missing": var_data.get("p_missing", 0),
            "distinct": {
                "count": var_data.get("n_distinct", 0),
                "percent": var_data.get("p_distinct", 0),
            },
        }

        # Type-specific metrics
        if var_type == "Numeric":
            var_metrics.update(
                {
                    "stats": {
                        "min": var_data.get("min", None),
                        "max": var_data.get("max", None),
                        "mean": var_data.get("mean", None),
                        "median": var_data.get("50%", var_data.get("median", None)),
                        "std": var_data.get("std", None),
                    }
                }
            )
        elif var_type == "Categorical" or var_type == "Text":
            if "value_counts_without_nan" in var_data:
                top_categories = dict(
                    list(var_data["value_counts_without_nan"].items())[:5]
                )
                var_metrics["top_categories"] = top_categories
        elif var_type == "DateTime":
            var_metrics.update(
                {
                    "range": {
                        "min": var_data.get("min", None),
                        "max": var_data.get("max", None),
                    }
                }
            )

        concise_profile["variables"][var_name] = var_metrics

    # Save to file
    output_path = output_dir / f"{title.lower().replace(' ', '_')}_profile.json"
    save_json_output(concise_profile, output_path)

    if logger:
        logger.debug(f"Saved LLM profile to {output_path}")
