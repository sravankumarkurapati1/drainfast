"""High-tide threshold and flags from NOAA station 8443970 (Boston), feet above MLLW."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TIDE_PERCENTILE = 95.0


def load_daily_max(path: Path) -> pd.Series:
    """Read the hourly tide CSV (t, v) and return the daily maximum level by date.

    t is already local station time (the spring-forward hour is a blank row), so the
    date is its first 10 characters. Rows with no water level are dropped.
    """
    raw = pd.read_csv(path, usecols=["t", "v"], dtype={"t": str})
    raw["v"] = pd.to_numeric(raw["v"], errors="coerce")
    raw = raw.dropna(subset=["v"])
    day = pd.to_datetime(raw["t"].str[:10]).dt.date
    return raw.groupby(day)["v"].max().sort_index()


def tide_threshold(daily_max: pd.Series, percentile: float = TIDE_PERCENTILE) -> float:
    """Return the given percentile of daily maximum levels, in feet."""
    if daily_max.empty:
        raise ValueError("no tide data to compute a threshold")
    return float(np.percentile(daily_max.to_numpy(), percentile))


def high_tide_days(daily_max: pd.Series, threshold: float) -> set:
    """Return the set of dates whose daily maximum is above the threshold."""
    return set(daily_max.index[daily_max.to_numpy() > threshold])


def threshold_record(daily_max: pd.Series, threshold: float, percentile: float = TIDE_PERCENTILE) -> dict:
    """Describe the threshold for tide_threshold.json."""
    return {
        "threshold_ft": round(threshold, 3),
        "percentile": percentile,
        "datum": "MLLW",
        "station": "8443970",
        "n_days": int(len(daily_max)),
        "first_day": str(daily_max.index.min()),
        "last_day": str(daily_max.index.max()),
    }
