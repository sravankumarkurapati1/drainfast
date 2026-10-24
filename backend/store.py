"""Load pipeline outputs from data/demo/, falling back to backend/fixtures/.

Each loader returns validated contract models. A missing or unreadable demo file never
stops the API: the matching fixture is used instead and `used_fixture` is logged.
"""
import json
import logging
import math
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, TypeVar

import pandas as pd
from pydantic import ValidationError

from backend.config import demo_dir, fixtures_dir
from backend.paths import RAW_DIR
from contracts.schemas import BacktestResult, Cell, ContractModel, RainTrendPoint, Report, Storm

log = logging.getLogger(__name__)
# Unreadable or malformed files (pyarrow errors subclass ValueError or OSError).
READ_ERRORS = (OSError, ValueError, KeyError, TypeError)
M = TypeVar("M", bound=ContractModel)


def _clean(value: Any) -> Any:
    """Turn pandas/numpy scalars into plain Python values that Pydantic accepts."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item") and not isinstance(value, (str, bytes, datetime, date)):
        return value.item()
    return value


def _validate_rows(rows: list[dict[str, Any]], model: type[M], source: str) -> list[M]:
    """Validate each row against the contract model; skip and log invalid ones.

    Columns that are not contract fields (pipeline extras such as `exclude` or
    `bwsc_share`) are dropped before validation, because contract models forbid extras.
    """
    out: list[M] = []
    bad = 0
    fields = set(model.model_fields)
    extras = sorted({k for row in rows[:1] for k in row} - fields)
    if extras:
        log.info("%s: ignoring non-contract columns %s", source, extras)
    for row in rows:
        try:
            out.append(model.model_validate({k: _clean(v) for k, v in row.items() if k in fields}))
        except ValidationError as e:
            bad += 1
            if bad <= 3:
                log.warning("%s: skipped invalid %s row: %s", source, model.__name__, e.errors()[:1])
    if bad:
        log.warning("%s: skipped %d invalid %s rows", source, bad, model.__name__)
    return out


def _read_file(path: Path) -> Optional[list[dict[str, Any]]]:
    """Read a .parquet or .json file into a list of dicts, or None when unavailable."""
    try:
        if not path.exists():
            return None
        if path.suffix == ".parquet":
            return pd.read_parquet(path).to_dict(orient="records")
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return data
        # Accept a wrapper object, e.g. {"points": [...], "slope_per_decade": ...} from
        # model.trend: use "points" or "items" if present, else the only list of records.
        if isinstance(data, dict):
            for key in ("points", "items"):
                if isinstance(data.get(key), list):
                    return data[key]
            records = [v for v in data.values()
                       if isinstance(v, list) and v and all(isinstance(x, dict) for x in v)]
            if len(records) == 1:
                return records[0]
        return None
    except READ_ERRORS as e:  # unreadable file: fall back, never crash
        log.warning("could not read %s: %s", path, e)
        return None


@lru_cache(maxsize=32)
def _load_cached(demo_path: str, mtime: float, fixture_name: str, model: type[M],
                 drop_excluded: bool) -> tuple[tuple[M, ...], bool]:
    """Read and validate one demo file (cached by path and mtime); fixture if unusable."""
    rows = _read_file(Path(demo_path))
    if rows is not None and drop_excluded:
        kept = [r for r in rows if not bool(_clean(r.get("exclude")) or False)]
        if len(kept) != len(rows):
            log.info("%s: dropped %d rows marked exclude", demo_path, len(rows) - len(kept))
        rows = kept
    if rows is not None:
        items = _validate_rows(rows, model, demo_path)
        if items:
            return tuple(items), False
    fixture = fixtures_dir() / fixture_name
    log.info("using fixture %s for %s", fixture, demo_path)
    return tuple(_validate_rows(_read_file(fixture) or [], model, str(fixture))), True


def _load(demo_name: str, fixture_name: str, model: type[M],
          drop_excluded: bool = False) -> tuple[list[M], bool]:
    """Return (items, used_fixture) for one demo file."""
    path = demo_dir() / demo_name
    mtime = path.stat().st_mtime if path.exists() else -1.0
    items, used_fixture = _load_cached(str(path), mtime, fixture_name, model, drop_excluded)
    return list(items), used_fixture


def load_reports() -> tuple[list[Report], bool]:
    """Storm-related 311 reports (data/demo/reports.parquet), without rows the pipeline
    marked `exclude` (test, invalid, wrong e-form or duplicate cases)."""
    return _load("reports.parquet", "report.json", Report, drop_excluded=True)


def load_cells() -> tuple[list[Cell], bool]:
    """All grid cells with flags (data/demo/cells.parquet)."""
    return _load("cells.parquet", "cell.json", Cell)


def load_storms() -> tuple[list[Storm], bool]:
    """Storm days with actual rain and tide (data/demo/storms.parquet)."""
    return _load("storms.parquet", "storm.json", Storm)


def load_backtest() -> tuple[list[BacktestResult], bool]:
    """Backtest results against both baselines (data/demo/backtest.json)."""
    return _load("backtest.json", "backtest_result.json", BacktestResult)


def load_rain_trend() -> tuple[list[RainTrendPoint], bool]:
    """Heavy-rain days per year (data/demo/rain_trend.json)."""
    return _load("rain_trend.json", "rain_trend_point.json", RainTrendPoint)


TIDE_RAW_FILE = ("tide", "boston_tide_hourly.csv")
TIDE_PERCENTILE = 0.95


def _threshold_from_file() -> Optional[float]:
    """Threshold from data/demo/tide_threshold.json, or None if missing or unreadable."""
    path = demo_dir() / "tide_threshold.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except READ_ERRORS as e:
        log.warning("could not read %s: %s", path, e)
        return None
    if isinstance(data, (int, float)):
        return float(data)
    if isinstance(data, dict):
        for k, v in data.items():
            if "threshold" in k and isinstance(v, (int, float)):
                return float(v)
    return None


@lru_cache(maxsize=1)
def _threshold_from_raw(path: str, mtime: float) -> Optional[float]:
    """95th percentile of daily maximum water level (ft MLLW) from the raw tide history."""
    try:
        df = pd.read_csv(path, usecols=["t", "v"])
        levels = pd.to_numeric(df["v"], errors="coerce")
        daily_max = levels.groupby(df["t"].str[:10]).max().dropna()
        return round(float(daily_max.quantile(TIDE_PERCENTILE)), 3) if len(daily_max) else None
    except READ_ERRORS as e:
        log.warning("could not compute tide threshold from %s: %s", path, e)
        return None


def tide_threshold_ft() -> Optional[float]:
    """High-tide threshold in feet MLLW.

    Prefers data/demo/tide_threshold.json (written by the model owner: a bare number, or
    an object with a numeric field whose name contains "threshold"). Until that file
    exists, uses the same definition as the V1 plan, the 95th percentile of daily
    maximum levels, computed from data/raw/tide. Returns None if neither is available.
    """
    value = _threshold_from_file()
    if value is not None:
        return value
    raw = RAW_DIR.joinpath(*TIDE_RAW_FILE)
    if not raw.exists():
        return None
    log.info("tide_threshold.json missing; using the 95th percentile of %s", raw)
    return _threshold_from_raw(str(raw), raw.stat().st_mtime)
