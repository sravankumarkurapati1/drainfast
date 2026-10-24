"""Heavy-rain days per year at Boston Logan, with a linear slope per decade."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from contracts.schemas import STORM_DAY_THRESHOLD_IN, RainTrendPoint


def rain_trend(daily: pd.DataFrame, threshold: float = STORM_DAY_THRESHOLD_IN) -> dict:
    """Count days with rain_total_in >= threshold per year.

    A leading year that does not start on January 1 is dropped (it is only the
    UTC-to-local spill of the first hours). A final year that does not reach
    December 31 is kept and named in partial_year, and is left out of the slope.
    Returns a dict with points (RainTrendPoint dicts), slope_per_decade and metadata.
    """
    days = pd.to_datetime(pd.Series(daily["storm_day"]))
    years = days.dt.year
    heavy = (daily["rain_total_in"].to_numpy() >= threshold)
    counts = pd.Series(heavy, index=years.to_numpy()).groupby(level=0).sum()
    first = days.groupby(years.to_numpy()).min()
    last = days.groupby(years.to_numpy()).max()

    starts_full = {y: first[y].date() == date(y, 1, 1) for y in counts.index}
    ends_full = {y: last[y].date() == date(y, 12, 31) for y in counts.index}
    keep = [y for y in counts.index if starts_full[y] or y != counts.index.min()]
    partial_year = next((y for y in keep if y == max(keep) and not ends_full[y]), None)
    full_years = [y for y in keep if starts_full[y] and ends_full[y]]

    points = [RainTrendPoint(year=int(y), heavy_rain_days=int(counts[y])).model_dump(mode="json") for y in keep]
    slope = None
    if len(full_years) >= 2:
        slope = float(np.polyfit(full_years, [counts[y] for y in full_years], 1)[0] * 10)
    return {
        "points": points,
        "slope_per_decade": None if slope is None else round(slope, 3),
        "partial_year": None if partial_year is None else int(partial_year),
        "threshold_in": threshold,
        "station": "BOS (Boston Logan)",
        "slope_years": [int(min(full_years)), int(max(full_years))] if full_years else None,
    }
