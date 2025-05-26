import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import yaml
from ydata_profiling import ProfileReport
from ydata_profiling.config import Settings

from cleaner.data_cleaner import DataCleaner
from cleaner.model_validators import ModelValidator


class PipelineOrchestrator:
    """
    Simplified orchestrator for data cleaning:
      1. Load & validate config
      2. Load raw data & simple raw checks
      3. Clean data via DataCleaner
      4. Simple post‐clean checks
      5. Save cleaned CSV
      6. (Optional) ydata profiling
      7. Log progress and errors
    """

    def __init__(self, config_path: Path, vector_store_client: Optional[Any] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = self._load_config(config_path)
        self.vector_store_client = vector_store_client
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        try:
            cfg_dict = yaml.safe_load(config_path.read_text())
            return cfg_dict  # Directly return the configuration dictionary
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise

    def _load_dataset(self, name: str) -> pd.DataFrame:
        ds_cfg = self.config["datasets"][name]
        # Use parent directory when running from cleaner/
        base_dir = Path(__file__).parent.parent
        path = base_dir / self.config["paths"]["raw_data"] / ds_cfg["file"]
        try:
            df = pd.read_csv(path)
            self.logger.info(f"[{name}] Loaded {len(df)} rows from {path}")
            return df
        except Exception as e:
            self.logger.error(f"[{name}] Failed to load raw data: {e}")
            raise

    def _check_data_quality(self, df: pd.DataFrame, name: str, stage: str) -> None:
        rows, cols = df.shape
        missing = int(df.isna().sum().sum())
        dupes = int(df.duplicated().sum()) if stage == "raw" else 0
        self.logger.info(
            f"[{name}|{stage}] rows={rows} cols={cols} "
            f"missing_cells={missing}" + (f" duplicates={dupes}" if dupes else "")
        )

    def _maybe_profile(
        self, name: str, raw: pd.DataFrame, cleaned: pd.DataFrame
    ) -> None:
        """Generate profiling reports if configured."""
        if "analysis" not in self.config:
            return

        prof_cfg = self.config["analysis"].get("profile")
        if not prof_cfg or not prof_cfg.get("minimal", False):
            return

        base_dir = Path(__file__).parent.parent
        out_dir = base_dir / self.config["paths"]["profiles"] / self.run_id / name
        out_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"[{name}] Generating ydata profiles in {out_dir}")

        # Create base profile configuration
        profile_settings = Settings()

        # Configure settings based on our config
        if isinstance(prof_cfg, dict):
            # Handle correlations
            if "correlations" in prof_cfg:
                for key, value in prof_cfg["correlations"].items():
                    if hasattr(profile_settings.correlations, key):
                        setattr(profile_settings.correlations, key, value)

            # Handle missing diagrams
            if "missing_diagrams" in prof_cfg:
                for key, value in prof_cfg["missing_diagrams"].items():
                    if hasattr(profile_settings.missing_diagrams, key):
                        setattr(profile_settings.missing_diagrams, key, value)

            # Handle variables configuration
            if "vars" in prof_cfg:
                if "cat" in prof_cfg["vars"]:
                    for key, value in prof_cfg["vars"]["cat"].items():
                        if hasattr(profile_settings.vars.cat, key):
                            setattr(profile_settings.vars.cat, key, value)
                if "num" in prof_cfg["vars"]:
                    for key, value in prof_cfg["vars"]["num"].items():
                        if hasattr(profile_settings.vars.num, key):
                            setattr(profile_settings.vars.num, key, value)

        try:
            # Create and save raw data profile
            raw_report = ProfileReport(
                raw,
                title=f"{name} raw",
                config=profile_settings,
                minimal=prof_cfg.get("minimal", True),
            )
            raw_report.to_file(out_dir / f"{name}_raw.html")

            # Create and save cleaned data profile
            cleaned_report = ProfileReport(
                cleaned,
                title=f"{name} cleaned",
                config=profile_settings,
                minimal=prof_cfg.get("minimal", True),
            )
            cleaned_report.to_file(out_dir / f"{name}_cleaned.html")

            # For comparison, ensure common columns have compatible types
            common_cols = list(set(raw.columns) & set(cleaned.columns))
            raw_compare = raw[common_cols].copy()
            cleaned_compare = cleaned[common_cols].copy()

            # Convert datetime columns to string for comparison
            datetime_cols = raw_compare.select_dtypes(
                include=["datetime64"]
            ).columns.tolist()
            for col in datetime_cols:
                raw_compare[col] = raw_compare[col].astype(str)
                cleaned_compare[col] = cleaned_compare[col].astype(str)

            # Convert structured columns to string for comparison
            for col in common_cols:
                if (
                    raw_compare[col].dtype == "object"
                    and cleaned_compare[col].dtype == "object"
                ):
                    raw_compare[col] = raw_compare[col].astype(str)
                    cleaned_compare[col] = cleaned_compare[col].astype(str)

            # Generate comparison report
            raw_compare_report = ProfileReport(
                raw_compare,
                title=f"{name} raw",
                config=profile_settings,
                minimal=prof_cfg.get("minimal", True),
            )
            cleaned_compare_report = ProfileReport(
                cleaned_compare,
                title=f"{name} cleaned",
                config=profile_settings,
                minimal=prof_cfg.get("minimal", True),
            )
            comparison = raw_compare_report.compare(cleaned_compare_report)
            comparison.to_file(out_dir / f"{name}_comparison.html")

        except Exception as e:
            self.logger.error(f"[{name}] Profile generation failed: {str(e)}")
            # Continue pipeline execution even if profiling fails
            return

    def process_dataset(self, name: str) -> bool:
        self.logger.info(f"--- Starting pipeline for {name} ---")
        try:
            raw_df = self._load_dataset(name)
            self._check_data_quality(raw_df, name, stage="raw")

            ds_cfg = self.config["datasets"][name]
            cleaner = DataCleaner(raw_df, ds_cfg["fields"])
            cleaned_df = cleaner.run()
            self._check_data_quality(cleaned_df, name, stage="cleaned")

            # 🆕 ADD MODEL VALIDATION HERE
            validator = ModelValidator(name)
            validated_df, validation_report = validator.validate_dataframe(cleaned_df)

            # Log validation results
            if not validation_report.get("skipped"):
                self.logger.info(
                    f"[{name}] Model validation: "
                    f"tested={validation_report['total_tested']}, "
                    f"errors={validation_report['validation_errors']}, "
                    f"fixed={validation_report['fixed_rows']}"
                )

                # Save validation report
                base_dir = Path(__file__).parent.parent
                run_dir = base_dir / self.config["paths"]["runs"] / self.run_id / name
                run_dir.mkdir(parents=True, exist_ok=True)

                import json

                with open(run_dir / f"{name}_validation_report.json", "w") as f:
                    json.dump(validation_report, f, indent=2, default=str)

            # Use validated_df for further processing
            final_df = validated_df
            self._check_data_quality(final_df, name, stage="validated")

            # Save cleaned data under runs/{run_id}/{dataset_name}
            base_dir = Path(__file__).parent.parent
            run_dir = base_dir / self.config["paths"]["runs"] / self.run_id / name
            run_dir.mkdir(parents=True, exist_ok=True)
            out_csv = run_dir / f"{name}_cleaned.csv"
            cleaned_df.to_csv(out_csv, index=False)
            self.logger.info(f"Saved cleaned CSV to {out_csv}")

            # If a vector_store_client is provided, save embeddings (for product bootstrap only)
            if self.vector_store_client is not None:
                from services.product.scripts.bootstrap.storage_manager import (
                    StorageManager,
                )

                storage = StorageManager(run_dir, cleaned_df, self.vector_store_client)
                storage.save_embeddings()

            # Optional profiling under analysis/profiles/{run_id}
            self._maybe_profile(name, raw_df, cleaned_df)

            # Update "latest" symlink to point to current run
            latest_dir = base_dir / self.config["paths"]["latest"] / name
            if latest_dir.exists():
                if latest_dir.is_symlink():
                    latest_dir.unlink()
                else:
                    shutil.rmtree(latest_dir)
            latest_dir.parent.mkdir(parents=True, exist_ok=True)
            latest_dir.symlink_to(run_dir)

            self.logger.info(f"--- Completed pipeline for {name} ---")
            return True

        except Exception as e:
            self.logger.error(f"[{name}] Pipeline failed: {e}")
            return False

    def run_all(self) -> bool:
        overall_success = True
        for ds in self.config["datasets"]:
            success = self.process_dataset(ds)
            overall_success = overall_success and success
        return overall_success


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.yaml")
    orchestrator = PipelineOrchestrator(cfg_path)
    success = orchestrator.run_all()
    sys.exit(0 if success else 1)
