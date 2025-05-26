# data_cleaner.py

import ast
import hashlib
import json
import re
import uuid
from typing import Any, Callable, Dict, List, Union

import pandas as pd

from cleaner.schema import FieldProcessingConfig
from cleaner.utils import normalize_text


class DataCleaner:
    """
    Config-driven data cleaning pipeline.
    Each field is processed according to its configuration.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        field_config: Dict[str, Any],
    ):
        self.df = df.copy()
        self.config = field_config

    def run(self) -> pd.DataFrame:
        """Process all fields according to their configs."""
        for field_name, field_config in self.config.items():
            # Convert dict config to FieldProcessingConfig
            if isinstance(field_config, dict):
                field_config = FieldProcessingConfig(**field_config)
            elif not isinstance(field_config, FieldProcessingConfig):
                raise ValueError(f"Invalid config type for {field_name}")

            if field_name not in self.df.columns:
                # Special handling for datetime combination
                if (
                    field_config.type == "datetime"
                    and "combine_datetime" in field_config.preprocessing
                ):
                    self.df[field_name] = self._process_field(
                        pd.Series(index=self.df.index), field_config, field_name
                    )
                continue
            processed = self._process_field(
                self.df[field_name], field_config, field_name
            )
            self.df[field_name] = processed

            # Add *_norm columns if requested
            if getattr(field_config, "add_norm_column", False):
                if field_config.type == "structured":
                    # Join list with space, then normalize
                    self.df[f"{field_name}_norm"] = processed.apply(
                        lambda x: normalize_text(
                            " ".join(x) if isinstance(x, list) else str(x)
                        )
                    )
                else:
                    self.df[f"{field_name}_norm"] = processed.apply(normalize_text)
        # NEW: Combine & checksum
        self.df["__embed_text"] = self.df.apply(self._make_doc_text, axis=1)
        self.df["embed_checksum"] = self.df["__embed_text"].apply(
            self._compute_checksum
        )
        # Add order_id if missing
        if "order_id" not in self.df.columns:
            self.df["order_id"] = [str(uuid.uuid4()) for _ in range(len(self.df))]
        self._convert_columns_to_snake_case()
        return self.df

    def _process_field(
        self, series: pd.Series, field_config: FieldProcessingConfig, field_name: str
    ) -> pd.Series:
        """Process a single field according to its config."""
        # First parse structured data if needed
        if field_config.type == "structured":
            parsed = series.apply(
                lambda x: self._parse_structured_data(
                    x, field_config.options.get("format", "list")
                )
            )

            if field_config.preserve_raw:
                # Always store the parsed list/dict as *_raw
                self.df[f"{field_name}_raw"] = parsed
                # For *_embed, join and normalize for embeddings
                self.df[f"{field_name}_embed"] = parsed.apply(
                    lambda lst: self._to_embedding_text(
                        lst, field_config.options, field_config
                    )
                )
                # Return parsed for main column (optional, not used downstream)
                return parsed
            else:
                return parsed
        else:
            # For non-structured fields, apply preprocessing first, then type processing
            processed = series

            # Apply preprocessing steps if specified
            if hasattr(field_config, "preprocessing") and field_config.preprocessing:
                for step in field_config.preprocessing:
                    processed = self._apply_preprocessing(
                        processed, step, field_config.options, field_config
                    )

            # Apply type-specific processing
            processor = self._get_processor(field_config.type)
            if processor:
                processed = processor(processed, field_config.options)

            # Handle preserve_raw logic
            if field_config.preserve_raw:
                # Store the basic cleaned version as *_raw
                raw_cleaned = self._basic_clean(series, field_config.type)
                self.df[f"{field_name}_raw"] = raw_cleaned
                # For *_embed, normalize for embeddings
                self.df[f"{field_name}_embed"] = raw_cleaned.apply(
                    lambda x: self._normalize_text(x, field_config.options)
                )

            return processed

    def _basic_clean(self, series: pd.Series, field_type: str) -> pd.Series:
        """Basic cleaning without normalization."""
        if field_type == "text":
            return series.fillna("").astype(str).apply(lambda x: str(x).strip())
        return series

    def _get_processor(self, field_type: str) -> Callable:
        """Returns the appropriate processor function for the field type."""
        processors = {
            "numeric": self._process_numeric,
            "text": self._process_text,
            "structured": self._process_structured,
            "categorical": self._process_categorical,
            "datetime": self._process_datetime,
        }
        return processors.get(field_type)

    def _process_numeric(self, series: pd.Series, options: Dict) -> pd.Series:
        """Process numeric fields."""
        # Clean the series first
        cleaned = series.replace(["None", "nan", "NaN", ""], pd.NA)

        # Try to convert to numeric, handling any invalid decimals
        def safe_numeric(val):
            if pd.isna(val):
                return pd.NA
            try:
                # Remove any currency symbols or commas
                if isinstance(val, str):
                    val = val.replace("$", "").replace(",", "").strip()
                return pd.to_numeric(val)
            except:
                return pd.NA

        return cleaned.apply(safe_numeric)

    def _process_structured(self, series: pd.Series, options: Dict) -> pd.Series:
        """Process structured data (lists/dicts)."""
        format_type = options.get("format", "list")

        def safe_parse(x):
            if pd.isna(x):
                return [] if format_type == "list" else {}
            try:
                return self._parse_structured_data(x, format_type)
            except Exception as e:
                return [] if format_type == "list" else {}

        return series.apply(safe_parse)

    def _process_text(self, series: pd.Series, options: Dict) -> pd.Series:
        """Process text fields."""
        return (
            series.fillna("")
            .astype(str)
            .apply(lambda x: self._normalize_text(x, options))
        )

    def _process_categorical(self, series: pd.Series, options: Dict) -> pd.Series:
        """Process categorical fields."""
        s = series.astype(str).str.strip()
        if options.get("lowercase", True):
            s = s.str.lower()
        if options.get("titlecase", True):
            s = s.str.title()
        if options.get("missing_fill"):
            s = s.fillna(options["missing_fill"])
        if options.get("drop_duplicates"):
            s = s.drop_duplicates()
        return s

    def _process_datetime(self, series: pd.Series, options: Dict) -> pd.Series:
        """Process datetime fields."""
        # First clean any invalid values
        cleaned = series.replace(["None", "nan", "NaN", ""], pd.NA)

        # Handle time-only fields
        if options.get("time_only", False):

            def parse_time(x):
                if pd.isna(x):
                    return None

                # For time fields, we want HH:MM:SS format
                if isinstance(x, str):
                    # If already in correct format, validate it
                    if re.match(r"^\d{2}:\d{2}:\d{2}$", x):
                        try:
                            # Validate the time components
                            hours, minutes, seconds = map(int, x.split(":"))
                            if (
                                0 <= hours <= 23
                                and 0 <= minutes <= 59
                                and 0 <= seconds <= 59
                            ):
                                return x
                        except ValueError:
                            return None

                    # Try to convert other time formats to HH:MM:SS
                    try:
                        dt = pd.to_datetime(x)
                        return dt.strftime("%H:%M:%S")
                    except:
                        return None

                # If it's already a datetime/timestamp, format it
                if isinstance(x, (pd.Timestamp, pd.datetime)):
                    return x.strftime("%H:%M:%S")

                return None

            return cleaned.apply(parse_time)

        # Handle date fields with strict format
        date_format = options.get("format")
        if date_format:
            # For dates, we want strict format enforcement
            try:
                result = pd.to_datetime(cleaned, format=date_format, errors="coerce")
                return result.where(result.notna(), None)
            except ValueError:
                # If strict parsing fails, return None - no flexible fallback
                return pd.Series([None] * len(cleaned))

        # No format specified, use flexible parsing (for non-Order_Date fields)
        result = pd.to_datetime(cleaned, errors="coerce")
        return result.where(result.notna(), None)

    def _parse_structured_data(self, val: Any, expected_type: str) -> Union[List, Dict]:
        """Parse string representations of structured data."""
        if pd.isna(val) or val is None:
            return [] if expected_type == "list" else {}

        if isinstance(val, (list, dict)):
            return val

        try:
            # Remove any unicode escape sequences first
            if isinstance(val, str):
                val = val.encode("utf-8").decode("unicode-escape")
            parsed = ast.literal_eval(str(val))
            if isinstance(parsed, (list, dict)):
                return parsed
            return [parsed] if expected_type == "list" else {"value": parsed}
        except Exception:
            if isinstance(val, str):
                # Try JSON parsing for dicts
                if expected_type == "dict" and val.strip().startswith("{"):
                    try:
                        return json.loads(val)
                    except Exception:
                        pass
                # Try comma splitting for lists
                if expected_type == "list" and "," in val:
                    return [x.strip() for x in val.split(",") if x.strip()]
            return [val] if expected_type == "list" else {"value": val}

    def _normalize_text(self, text: str, options: Dict = None) -> str:
        """Normalize text content. Handles both strings and lists."""
        options = options or {}

        if isinstance(text, list):
            # Normalize each item, join with ". "
            cleaned = [
                self._normalize_text(item, options)
                for item in text
                if pd.notna(item) and str(item).strip()
            ]
            return ". ".join(cleaned)

        if pd.isna(text) or text is None:
            return ""

        text = str(text).strip()
        if options.get("remove_html", True):
            text = re.sub(r"<[^>]+>", " ", text)
        if options.get("lowercase", True):
            text = text.lower()
        if options.get("remove_special_chars", True):
            text = re.sub(r"[^\w\s.,!?-]", " ", text)
        return " ".join(text.split())

    def _to_embedding_text(
        self, lst: Any, options: Dict, field_config: FieldProcessingConfig
    ) -> str:
        """Convert a list or string to embedding-friendly text."""
        min_length = field_config.min_token_length
        if isinstance(lst, list):
            cleaned_items = []
            for item in lst:
                if pd.isna(item) or item is None:
                    continue
                text = str(item).strip()
                if len(text) >= min_length:
                    text = re.sub(r"[^\w\s.,!?-]", " ", text)
                    text = " ".join(text.split())
                    if text:
                        cleaned_items.append(text.lower())
            return ". ".join(cleaned_items)
        else:
            if pd.isna(lst) or lst is None:
                return ""
            text = str(lst).strip()
            if len(text) >= min_length:
                text = re.sub(r"[^\w\s.,!?-]", " ", text)
                text = " ".join(text.split())
                return text.lower()
            return ""

    def _apply_preprocessing(
        self,
        series: pd.Series,
        step: str,
        options: Dict,
        field_config: FieldProcessingConfig,
    ) -> pd.Series:
        """Apply a preprocessing step to a series."""
        preprocessors = {
            "normalize_text": lambda s: s.apply(
                lambda x: self._normalize_text(x, options)
            ),
            "join_text": lambda s: s.apply(
                lambda x: options.get("join_separator", " ").join(x)
                if isinstance(x, list)
                else x
            ),
            "to_embedding_text": lambda s: s.apply(
                lambda x: self._to_embedding_text(x, options, field_config)
            ),
            "combine_datetime": lambda s: self._combine_datetime(self.df, options),
        }
        preprocessor = preprocessors.get(step)
        return preprocessor(series) if preprocessor else series

    def _combine_datetime(self, df: pd.DataFrame, options: Dict) -> pd.Series:
        """Combine date and time fields into a single datetime."""
        date_series = options.get("date_series")
        time_series = options.get("time_series")
        timezone = options.get("timezone", "UTC")

        if not date_series or not time_series:
            raise ValueError("Both date_series and time_series must be specified")

        if date_series not in df.columns or time_series not in df.columns:
            raise ValueError(f"Missing required series: {date_series} or {time_series}")

        def parse_time(t):
            """Parse time string to datetime.time object."""
            if pd.isna(t):
                return None

            # We expect time to be in HH:MM:SS format
            if not isinstance(t, str) or not re.match(r"^\d{2}:\d{2}:\d{2}$", t):
                return None

            try:
                hours, minutes, seconds = map(int, t.split(":"))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59):
                    return None
                return (
                    pd.Timestamp.now()
                    .replace(hour=hours, minute=minutes, second=seconds, microsecond=0)
                    .time()
                )
            except:
                return None

        def combine_dt(row):
            """Combine date and time into datetime with timezone."""
            date_str = row[date_series]
            time_str = row[time_series]

            # Skip if either component is missing
            if pd.isna(date_str) or pd.isna(time_str):
                return None

            # Parse the time string into a time object
            time_obj = parse_time(time_str)
            if time_obj is None:
                return None

            try:
                # Parse the date string if needed
                if isinstance(date_str, str):
                    try:
                        date = pd.to_datetime(date_str, format="%Y-%m-%d")
                    except ValueError:
                        return None
                else:
                    date = date_str

                if pd.isna(date):
                    return None

                # Create a new timestamp with both date and time components
                dt = pd.Timestamp(
                    year=date.year,
                    month=date.month,
                    day=date.day,
                    hour=time_obj.hour,
                    minute=time_obj.minute,
                    second=time_obj.second,
                )

                # Localize to specified timezone
                if timezone:
                    dt = dt.tz_localize(timezone)
                return dt
            except Exception as e:
                print(f"Error combining datetime: {e}")  # Debug info
                return None

        return df.apply(combine_dt, axis=1)

    def _make_doc_text(self, row: pd.Series) -> str:
        parts = []
        # Dynamically include fields with 'to_embedding_text' in preprocessing
        for field_name, field_config in self.config.items():
            # Convert dict config to FieldProcessingConfig if needed
            if isinstance(field_config, dict):
                field_config = FieldProcessingConfig(**field_config)
            if "to_embedding_text" in getattr(field_config, "preprocessing", []):
                embed_col = f"{field_name}_embed"
                if (
                    embed_col in row
                    and pd.notna(row[embed_col])
                    and str(row[embed_col]).strip()
                ):
                    tag = field_name.upper()
                    parts.append(f"<{tag}> {row[embed_col]} </{tag}>")

        combined_text = "\n".join(parts)

        # Fallback if empty embed text (prevents 118 bootstrap failures)
        if not combined_text.strip():
            # Use title + ASIN as minimum fallback
            title = row.get("title_raw", row.get("title", ""))
            asin = row.get("parent_asin", "")
            if title or asin:
                combined_text = f"<TITLE> {title} </TITLE>\n<ASIN> {asin} </ASIN>"
            else:
                # Last resort - use any available text field
                for col in row.index:
                    if pd.notna(row[col]) and str(row[col]).strip():
                        combined_text = f"<DATA> {str(row[col]).strip()} </DATA>"
                        break

        return combined_text

    @staticmethod
    def _compute_checksum(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _convert_columns_to_snake_case(self):
        """Convert all DataFrame columns to snake_case."""

        def to_snake(name):
            name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
            name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
            name = name.replace(" ", "_")
            return name.lower()

        self.df.columns = [to_snake(col) for col in self.df.columns]
