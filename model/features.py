"""Per-cell features for one date, using only reports opened strictly before as_of."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd

from contracts.schemas import CauseLabel
from model import paths

log = logging.getLogger(__name__)

LOCAL_TZ = "America/New_York"
DAYS_SINCE_CAP = 3650
LEAF_MONTHS = (10, 11)
FEATURES: tuple[str, ...] = (
    "past_fixable_count",
    "past_fixable_365d",
    "past_total_reports",
    "days_since_last_fixable",
    "leaf_season",
    "rain_in",
    "high_tide",
)


def as_local_date(value: date | datetime) -> date:
    """Return the America/New_York calendar date of a date or datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return pd.Timestamp(value).tz_convert(LOCAL_TZ).date()
        return value.date()
    return value


def prepare_reports(reports: pd.DataFrame) -> pd.DataFrame:
    """Keep usable reports and add the columns features need.

    Drops excluded rows (test, invalid, duplicate notes) and reports marked as
    duplicates. Returns ticket_id, cell_id, day (local midnight, naive) and fixable
    (cause_label is clogged_basin), sorted by day then ticket_id.
    """
    df = reports
    if "exclude" in df.columns:
        df = df[~df["exclude"].fillna(False).astype(bool)]
    if "duplicate_of" in df.columns:
        df = df[df["duplicate_of"].isna()]
    opened = pd.to_datetime(df["opened_at"], utc=True).dt.tz_convert(LOCAL_TZ)
    out = pd.DataFrame({
        "ticket_id": df["ticket_id"].astype(str).to_numpy(),
        "cell_id": df["cell_id"].astype(str).to_numpy(),
        "day": opened.dt.tz_localize(None).dt.normalize().to_numpy(),
        "fixable": (df["cause_label"].astype(str) == CauseLabel.clogged_basin.value).to_numpy(),
    })
    return out.sort_values(["day", "ticket_id"], kind="stable").reset_index(drop=True)


def load_reports(reports_path: Path = paths.REPORTS_PATH, fixture_path: Path = paths.FIXTURE_REPORTS_PATH) -> pd.DataFrame:
    """Load reports.parquet, or the contract fixture when it is missing. Returns prepared reports."""
    if reports_path.exists():
        return prepare_reports(pd.read_parquet(reports_path))
    if fixture_path.exists():
        log.warning("%s missing; using %s", reports_path, fixture_path)
        return prepare_reports(pd.DataFrame(json.loads(fixture_path.read_text(encoding="utf-8"))))
    raise FileNotFoundError(f"neither {reports_path} nor {fixture_path} exists; run `make data` first")


def load_cell_ids(cells_path: Path = paths.CELLS_PATH, reports: pd.DataFrame | None = None) -> list[str]:
    """Return sorted cell ids from cells.parquet, or from the reports when it is missing."""
    if cells_path.exists():
        return sorted(pd.read_parquet(cells_path, columns=["cell_id"])["cell_id"].astype(str).unique())
    if reports is None:
        raise FileNotFoundError(f"{cells_path} missing; run `make cells` first")
    log.warning("%s missing; using the cells that have reports", cells_path)
    return sorted(reports["cell_id"].unique())


@lru_cache(maxsize=1)
def default_inputs() -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Load prepared reports and cell ids from data/demo once per process."""
    reports = load_reports()
    return reports, tuple(load_cell_ids(reports=reports))


def build_features(
    as_of: date | datetime,
    rain_in: float,
    high_tide: bool,
    reports: pd.DataFrame | None = None,
    cell_ids: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Build one feature row per cell for the storm on as_of.

    Inputs: as_of (date; never today's date implicitly), rain_in (inches), high_tide,
    and optionally prepared reports and cell ids (default: data/demo). Only reports
    opened strictly before as_of's local date are used. Output: cell_id plus FEATURES,
    sorted by cell_id.
    """
    if reports is None or cell_ids is None:
        default_reports, default_cells = default_inputs()
        reports = default_reports if reports is None else reports
        cell_ids = default_cells if cell_ids is None else cell_ids
    day = as_local_date(as_of)
    cutoff = pd.Timestamp(day)
    index = pd.Index(sorted(set(cell_ids)), name="cell_id")

    past = reports[reports["day"] < cutoff]
    fixable = past[past["fixable"]]
    recent = fixable[fixable["day"] >= cutoff - pd.Timedelta(days=365)]
    last_fixable = fixable.groupby("cell_id")["day"].max()
    days_since = (cutoff - last_fixable).dt.days.clip(upper=DAYS_SINCE_CAP)

    out = pd.DataFrame(index=index)
    out["past_fixable_count"] = fixable.groupby("cell_id").size().reindex(index, fill_value=0).astype(float)
    out["past_fixable_365d"] = recent.groupby("cell_id").size().reindex(index, fill_value=0).astype(float)
    out["past_total_reports"] = past.groupby("cell_id").size().reindex(index, fill_value=0).astype(float)
    out["days_since_last_fixable"] = days_since.reindex(index).fillna(DAYS_SINCE_CAP).astype(float)
    out["leaf_season"] = float(day.month in LEAF_MONTHS)
    out["rain_in"] = float(rain_in)
    out["high_tide"] = float(bool(high_tide))
    return out.reset_index()
