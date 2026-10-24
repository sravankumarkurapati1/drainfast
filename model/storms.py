"""Daily rain at Boston Logan and storm days (1.0 inch or more by default)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from contracts.schemas import STORM_DAY_THRESHOLD_IN, Storm

LOCAL_TZ = "America/New_York"
_SHIFT = pd.Timedelta(minutes=6)


def load_hourly_rain(path: Path) -> pd.DataFrame:
    """Read the IEM export (station, valid, p01i). Returns valid_utc and p (inches).

    valid is UTC. p01i values M (missing) and T (trace) count as 0.
    """
    raw = pd.read_csv(path, dtype={"p01i": str})
    p = pd.to_numeric(raw["p01i"].replace({"M": "0", "T": "0"}), errors="coerce").fillna(0.0)
    valid = pd.to_datetime(raw["valid"]).dt.tz_localize("UTC")
    return pd.DataFrame({"valid_utc": valid, "p": p.clip(lower=0.0)})


def hourly_totals(rain: pd.DataFrame) -> pd.DataFrame:
    """Collapse to one value per hourly accumulation period.

    ASOS reports rain since the last routine :54 observation, so a special report
    (for example at :20) repeats rain the :54 report also includes. Each period
    (previous :54, this :54] is keyed by shifting 6 minutes and rounding up to the
    hour, in UTC so daylight saving time cannot create ambiguous hours. The period
    total is the largest reading in it. Returns valid_local (the :54 time) and p.
    """
    key = (rain["valid_utc"] + _SHIFT).dt.ceil("h")
    per_hour = rain.groupby(key)["p"].max()
    valid_local = (per_hour.index - _SHIFT).tz_convert(LOCAL_TZ)
    return pd.DataFrame({"valid_local": valid_local, "p": per_hour.to_numpy()})


def daily_rain(hourly: pd.DataFrame) -> pd.DataFrame:
    """Sum hourly totals by local day. Returns storm_day, rain_total_in, max_hourly_in."""
    day = hourly["valid_local"].dt.date
    grouped = hourly.groupby(day)["p"]
    out = pd.DataFrame({
        "rain_total_in": grouped.sum().round(2),
        "max_hourly_in": grouped.max().round(2),
    })
    out.index.name = "storm_day"
    return out.reset_index().sort_values("storm_day", kind="stable").reset_index(drop=True)


def build_storm_table(daily: pd.DataFrame, high_tide_days: set, threshold: float = STORM_DAY_THRESHOLD_IN) -> pd.DataFrame:
    """Add high_tide_flag and is_storm_day to the daily rain table.

    Inputs: daily rain (storm_day, rain_total_in, max_hourly_in), the set of dates with
    a high tide, and the storm threshold in inches. Output: one row per day.
    """
    out = daily.copy()
    out["high_tide_flag"] = out["storm_day"].isin(high_tide_days)
    out["is_storm_day"] = out["rain_total_in"] >= threshold
    return out[["storm_day", "rain_total_in", "max_hourly_in", "high_tide_flag", "is_storm_day"]]


def validate_storms(storms: pd.DataFrame) -> None:
    """Validate every row as contracts.schemas.Storm; raise ValueError on the first bad day."""
    cols = ["storm_day", "rain_total_in", "max_hourly_in", "high_tide_flag"]
    for row in storms[cols].to_dict("records"):
        try:
            Storm.model_validate({
                "storm_day": row["storm_day"],
                "rain_total_in": float(row["rain_total_in"]),
                "max_hourly_in": float(row["max_hourly_in"]),
                "high_tide_flag": bool(row["high_tide_flag"]),
            })
        except Exception as exc:
            raise ValueError(f"storm day {row['storm_day']} is not a valid Storm: {exc}") from exc
