# data_cleaner.py

import ast
import hashlib
import json
import re
import uuid
from typing import Any, Callable, Dict, List, Union

import pandas as pd

from cleaner.schema import FieldProcessingConfig


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
        for field_name, field_cfg in self.config.items():
            # normalize config into FieldProcessingConfig
            if isinstance(field_cfg, dict):
                field_cfg = FieldProcessingConfig(**field_cfg)
            elif not isinstance(field_cfg, FieldProcessingConfig):
                raise ValueError(f"Invalid config type for {field_name}")

            if field_name not in self.df.columns:
                # handle combine_datetime when missing
                if (
                    field_cfg.type == "datetime"
                    and "combine_datetime" in field_cfg.preprocessing
                ):
                    self.df[field_name] = self._process_field(
                        pd.Series(index=self.df.index), field_cfg, field_name
                    )
                continue

            processed = self._process_field(self.df[field_name], field_cfg, field_name)
            self.df[field_name] = processed

        # Combine for embeddings & checksum
        self.df["__embed_text"] = self.df.apply(self._make_doc_text, axis=1)
        self.df["embed_checksum"] = self.df["__embed_text"].apply(
            self._compute_checksum
        )

        # Ensure order_id exists
        if "order_id" not in self.df.columns:
            self.df["order_id"] = [str(uuid.uuid4()) for _ in range(len(self.df))]

        self._convert_columns_to_snake_case()
        return self.df

    def _process_field(
        self, series: pd.Series, cfg: FieldProcessingConfig, name: str
    ) -> pd.Series:
        """Process a single field according to its config."""
        if cfg.type == "structured":
            parsed = self._process_structured(series, cfg.options)
            if cfg.preserve_raw:
                self.df[f"{name}_raw"] = parsed
                self.df[f"{name}_embed"] = parsed.apply(
                    lambda lst: self._to_embedding_text(lst, cfg.options, cfg)
                )
            return parsed

        s = series
        if cfg.preprocessing:
            for step in cfg.preprocessing:
                s = self._apply_preprocessing(s, step, cfg.options, cfg)

        proc = self._get_processor(cfg.type)
        if proc:
            s = proc(s, cfg.options)

        if cfg.preserve_raw:
            raw = self._basic_clean(series, cfg.type)
            self.df[f"{name}_raw"] = raw
            self.df[f"{name}_embed"] = raw.apply(
                lambda x: self._normalize_text(x, cfg.options)
            )

        return s

    def _basic_clean(self, series: pd.Series, ftype: str) -> pd.Series:
        if ftype == "text":
            return series.fillna("").astype(str).str.strip()
        return series

    def _get_processor(self, ftype: str) -> Callable:
        return {
            "numeric": self._process_numeric,
            "text": self._process_text,
            "structured": self._process_structured,
            "categorical": self._process_categorical,
            "datetime": self._process_datetime,
        }.get(ftype)

    def _process_numeric(self, series: pd.Series, opts: Dict) -> pd.Series:
        cleaned = series.replace(["None", "nan", "NaN", ""], pd.NA)

        def safe(val):
            if pd.isna(val):
                return pd.NA
            try:
                if isinstance(val, str):
                    val = val.replace("$", "").replace(",", "").strip()
                return pd.to_numeric(val)
            except:
                return pd.NA

        return cleaned.apply(safe)

    def _process_structured(self, series: pd.Series, opts: Dict) -> pd.Series:
        fmt = opts.get("format", "list")
        lc = opts.get("lowercase", False)

        def parse(x):
            if pd.isna(x):
                return [] if fmt == "list" else {}
            parsed = self._parse_structured_data(x, fmt)
            if lc:
                if fmt == "list" and isinstance(parsed, list):
                    return [
                        str(i).lower().strip() if isinstance(i, str) else i
                        for i in parsed
                    ]
                if fmt == "dict" and isinstance(parsed, dict):
                    return {
                        k: (str(v).lower().strip() if isinstance(v, str) else v)
                        for k, v in parsed.items()
                    }
            return parsed

        return series.apply(parse)

    def _process_text(self, series: pd.Series, opts: Dict) -> pd.Series:
        return (
            series.fillna("").astype(str).apply(lambda x: self._normalize_text(x, opts))
        )

    def _process_categorical(self, series: pd.Series, opts: Dict) -> pd.Series:
        s = series.astype(str).str.strip()
        if opts.get("lowercase"):
            s = s.str.lower()
        if opts.get("titlecase"):
            s = s.str.title()
        if opts.get("missing_fill"):
            s = s.fillna(opts["missing_fill"])
        if opts.get("drop_duplicates"):
            s = s.drop_duplicates()
        return s

    def _process_datetime(self, series: pd.Series, opts: Dict) -> pd.Series:
        clean = series.replace(["None", "nan", "NaN", ""], pd.NA)
        if opts.get("time_only"):

            def pt(x):
                if pd.isna(x):
                    return None
                if isinstance(x, str) and re.match(r"^\d{2}:\d{2}:\d{2}$", x):
                    return x
                try:
                    return pd.to_datetime(x).strftime("%H:%M:%S")
                except:
                    return None

            return clean.apply(pt)

        fmt = opts.get("format")
        if fmt:
            return pd.to_datetime(clean, format=fmt, errors="coerce").where(
                lambda v: v.notna(), None
            )
        return pd.to_datetime(clean, errors="coerce").where(lambda v: v.notna(), None)

    def _parse_structured_data(self, val: Any, expected: str) -> Union[List, Dict]:
        if pd.isna(val) or val is None:
            return [] if expected == "list" else {}
        if isinstance(val, (list, dict)):
            return val

        txt = val
        if isinstance(txt, str):
            txt = txt.encode("utf-8").decode("unicode-escape")
        try:
            lit = ast.literal_eval(str(txt))
            if isinstance(lit, (list, dict)):
                return lit
            return [lit] if expected == "list" else {"value": lit}
        except:
            if isinstance(txt, str):
                if expected == "dict" and txt.strip().startswith("{"):
                    try:
                        return json.loads(txt)
                    except:
                        pass
                if expected == "list" and "," in txt:
                    return [x.strip() for x in txt.split(",") if x.strip()]
            return [txt] if expected == "list" else {"value": txt}

    def _normalize_text(self, text: str, opts: Dict = None) -> str:
        opts = opts or {}
        if isinstance(text, list):
            return ". ".join(
                self._normalize_text(item, opts)
                for item in text
                if pd.notna(item) and str(item).strip()
            )
        if pd.isna(text) or text is None:
            return ""
        s = str(text).strip()
        if opts.get("remove_html", True):
            s = re.sub(r"<[^>]+>", " ", s)
        if opts.get("lowercase", False):
            s = s.lower()
        if opts.get("remove_special_chars", True):
            s = re.sub(r"[^\w\s.,!?-]", " ", s)
        return " ".join(s.split())

    def _to_embedding_text(
        self, lst: Any, opts: Dict, cfg: FieldProcessingConfig
    ) -> str:
        ml = cfg.min_token_length
        if isinstance(lst, list):
            out = []
            for i in lst:
                if pd.isna(i):
                    continue
                t = str(i).strip()
                if len(t) >= ml:
                    t = re.sub(r"[^\w\s.,!?-]", " ", t)
                    t = " ".join(t.split())
                    if t:
                        out.append(t.lower())
            return ". ".join(out)

        t = "" if pd.isna(lst) else str(lst).strip()
        if len(t) >= ml:
            t = re.sub(r"[^\w\s.,!?-]", " ", t)
            t = " ".join(t.split())
            return t.lower()
        return ""

    def _apply_preprocessing(
        self, series: pd.Series, step: str, opts: Dict, cfg: FieldProcessingConfig
    ) -> pd.Series:
        procs = {
            "normalize_text": lambda s: s.apply(
                lambda x: self._normalize_text(x, opts)
            ),
            "join_text": lambda s: s.apply(
                lambda x: opts.get("join_separator", " ").join(x)
                if isinstance(x, list)
                else x
            ),
            "to_embedding_text": lambda s: s.apply(
                lambda x: self._to_embedding_text(x, opts, cfg)
            ),
            "combine_datetime": lambda s: self._combine_datetime(self.df, opts),
            "lowercase": lambda s: s.apply(lambda x: self._apply_lowercase_to_data(x)),
        }
        fn = procs.get(step)
        return fn(series) if fn else series

    def _apply_lowercase_to_data(self, v):
        if pd.isna(v) or v is None:
            return v
        if isinstance(v, str):
            return v.lower().strip()
        if isinstance(v, list):
            return [str(i).lower().strip() if isinstance(i, str) else i for i in v]
        if isinstance(v, dict):
            return {
                k: (str(vv).lower().strip() if isinstance(vv, str) else vv)
                for k, vv in v.items()
            }
        return str(v).lower().strip()

    def _combine_datetime(self, df: pd.DataFrame, opts: Dict) -> pd.Series:
        ds, ts = opts.get("date_series"), opts.get("time_series")
        tz = opts.get("timezone", "UTC")
        if not ds or not ts:
            raise ValueError("date_series & time_series required")
        if ds not in df or ts not in df:
            raise ValueError(f"Missing series: {ds} or {ts}")

        def pt(t):
            if pd.isna(t):
                return None
            if isinstance(t, str) and re.match(r"^\d{2}:\d{2}:\d{2}$", t):
                return t
            try:
                return pd.to_datetime(t).strftime("%H:%M:%S")
            except:
                return None

        def cb(row):
            d, ti = row[ds], row[ts]
            if pd.isna(d) or pd.isna(ti):
                return None
            to = pt(ti)
            if to is None:
                return None
            try:
                date = (
                    pd.to_datetime(d, format="%Y-%m-%d", errors="coerce")
                    if isinstance(d, str)
                    else d
                )
                if pd.isna(date):
                    return None
                dt = pd.Timestamp(
                    year=date.year,
                    month=date.month,
                    day=date.day,
                    hour=int(to[:2]),
                    minute=int(to[3:5]),
                    second=int(to[6:8]),
                )
                return dt.tz_localize(tz) if tz else dt
            except:
                return None

        return df.apply(cb, axis=1)

    def _make_doc_text(self, row: pd.Series) -> str:
        parts = []
        for name, cfg in self.config.items():
            if isinstance(cfg, dict):
                cfg = FieldProcessingConfig(**cfg)
            if "to_embedding_text" in cfg.preprocessing:
                col = f"{name}_embed"
                if col in row and pd.notna(row[col]) and str(row[col]).strip():
                    T = name.upper()
                    parts.append(f"<{T}> {row[col]} </{T}>")
        txt = "\n".join(parts)
        if not txt.strip():
            title = row.get("title_raw", row.get("title", ""))
            asin = row.get("parent_asin", "")
            if title or asin:
                return f"<TITLE> {title} </TITLE>\n<ASIN> {asin} </ASIN>"
            for c in row.index:
                if pd.notna(row[c]) and str(row[c]).strip():
                    return f"<DATA> {row[c]} </DATA>"
        return txt

    @staticmethod
    def _compute_checksum(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _convert_columns_to_snake_case(self):
        def to_snake(n):
            n = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", n)
            n = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", n)
            return n.replace(" ", "_").lower()

        self.df.columns = [to_snake(c) for c in self.df.columns]
