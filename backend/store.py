"""Load pipeline outputs from data/demo/, falling back to contracts/fixtures/.

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
from contracts.schemas import BacktestResult, Cell, ContractModel, RainTrendPoint, Report, Storm

log = logging.getLogger(__name__)
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
    """Validate each row; skip and log invalid ones so one bad row never breaks the app."""
    out: list[M] = []
    bad = 0
    for row in rows:
        try:
            out.append(model.model_validate({k: _clean(v) for k, v in row.items()}))
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
        return data if isinstance(data, list) else None
    except Exception as e:  # unreadable file: fall back, never crash
        log.warning("could not read %s: %s", path, e)
        return None


@lru_cache(maxsize=32)
def _load_cached(demo_path: str, mtime: float, fixture_name: str, model: type[M]) -> tuple[tuple[M, ...], bool]:
    rows = _read_file(Path(demo_path))
    if rows is not None:
        items = _validate_rows(rows, model, demo_path)
        if items:
            return tuple(items), False
    fixture = fixtures_dir() / fixture_name
    log.info("using fixture %s for %s", fixture, demo_path)
    return tuple(_validate_rows(_read_file(fixture) or [], model, str(fixture))), True


def _load(demo_name: str, fixture_name: str, model: type[M]) -> tuple[list[M], bool]:
    """Return (items, used_fixture) for one demo file."""
    path = demo_dir() / demo_name
    mtime = path.stat().st_mtime if path.exists() else -1.0
    items, used_fixture = _load_cached(str(path), mtime, fixture_name, model)
    return list(items), used_fixture


def load_reports() -> tuple[list[Report], bool]:
    """All storm-related 311 reports (data/demo/reports.parquet)."""
    return _load("reports.parquet", "report.json", Report)


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


def tide_threshold_ft() -> Optional[float]:
    """High-tide threshold in feet MLLW from data/demo/tide_threshold.json, or None.

    Accepts a bare number or an object with one numeric field whose name contains
    "threshold" (the model owner picks the key).
    """
    path = demo_dir() / "tide_threshold.json"
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    if isinstance(data, (int, float)):
        return float(data)
    if isinstance(data, dict):
        for k, v in data.items():
            if "threshold" in k and isinstance(v, (int, float)):
                return float(v)
    return None
