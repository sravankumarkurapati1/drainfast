"""Read the raw 311 export and turn it into clean, labeled Report rows."""
from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from contracts.cells import cell_id
from data_pipeline.geo import points_in_area
from data_pipeline.labeler import NoteLabeler, label_note
from data_pipeline.notes import is_excluded, normalize_text, split_closure

log = logging.getLogger(__name__)
TZ = "America/New_York"

# Every reason a row can be dropped, in the order they are checked.
DROP_REASONS: tuple[str, ...] = (
    "missing_coordinates",
    "city_hall_placeholder",
    "bad_open_dt",
    "unknown_status",
    "closed_before_opened",
)
REQUIRED_COLUMNS: tuple[str, ...] = (
    "case_enquiry_id", "open_dt", "closed_dt", "case_status", "closure_reason",
    "case_title", "latitude", "longitude", "neighborhood", "location",
)
# Report fields (contracts.schemas.Report) in contract order, then pipeline-only columns.
REPORT_COLUMNS: tuple[str, ...] = (
    "ticket_id", "opened_at", "closed_at", "status", "lat", "lon", "cell_id", "text",
    "closing_note", "note_blank", "cause_label", "label_source", "storm_day",
    "neighborhood", "ej_flag", "duplicate_of",
)
EXTRA_COLUMNS: tuple[str, ...] = ("exclude",)
_CITY_HALL = re.compile(r"\b1\s+city\s+hall\s+(?:plz|plaza)\b", re.IGNORECASE)


def load_raw(path: Path) -> pd.DataFrame:
    """Read the 311 CSV as strings, with empty cells kept as ""."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    return df


def parse_local_times(values: pd.Series) -> pd.Series:
    """Parse mixed-format local Boston timestamps into tz-aware America/New_York values.

    Blank or unparseable values become NaT. Ambiguous fall-back hours are read as
    standard time and missing spring-forward hours shift forward, so DST loses no rows.
    """
    text = values.fillna("").astype(str).str.strip().replace("", None)
    parsed = pd.to_datetime(text, format="mixed", errors="coerce")
    if getattr(parsed.dt, "tz", None) is not None:
        return parsed.dt.tz_convert(TZ)
    return parsed.dt.tz_localize(
        TZ, ambiguous=np.zeros(len(parsed), dtype=bool), nonexistent="shift_forward"
    )


def _drop(df: pd.DataFrame, mask: pd.Series, reason: str, drops: Counter[str]) -> pd.DataFrame:
    n = int(mask.sum())
    if n:
        drops[reason] += n
        log.info("dropped %d rows: %s", n, reason)
    return df.loc[~mask]


def clean_reports(
    raw: pd.DataFrame,
    ej_area: object | None = None,
    llm: NoteLabeler | None = None,
) -> tuple[pd.DataFrame, Counter[str]]:
    """Turn raw 311 rows into Report rows plus an `exclude` column.

    Returns (reports, drops) where drops counts removed rows per reason in DROP_REASONS.
    Kept rows + sum(drops) always equals len(raw).
    """
    drops: Counter[str] = Counter()
    df = raw.copy()

    df["lat"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["lon"] = pd.to_numeric(df["longitude"], errors="coerce")
    bad_coords = (
        df["lat"].isna() | df["lon"].isna()
        | ~np.isfinite(df["lat"]) | ~np.isfinite(df["lon"])
        | (df["lat"].abs() > 90) | (df["lon"].abs() > 180)
    )
    df = _drop(df, bad_coords, "missing_coordinates", drops)

    location = df["location"].map(normalize_text)
    df = _drop(df, location.str.contains(_CITY_HALL), "city_hall_placeholder", drops)

    df["opened_at"] = parse_local_times(df["open_dt"])
    df = _drop(df, df["opened_at"].isna(), "bad_open_dt", drops)

    df["status"] = df["case_status"].str.strip().str.lower()
    df = _drop(df, ~df["status"].isin(["open", "closed"]), "unknown_status", drops)

    closed_at = parse_local_times(df["closed_dt"])
    df["closed_at"] = closed_at.where(df["status"] == "closed")
    df = _drop(df, df["closed_at"].notna() & (df["closed_at"] < df["opened_at"]),
               "closed_before_opened", drops)

    split = df["closure_reason"].map(split_closure)
    notes = split.map(lambda t: t[0])
    statuses = split.map(lambda t: t[1])
    df["note_blank"] = notes.eq("")
    df["closing_note"] = notes.where(~df["note_blank"], None)
    df["exclude"] = [is_excluded(n, s) for n, s in zip(notes, statuses)]

    # Label each distinct (note, exclude) once, so the LLM sees each note at most once.
    labels: dict[tuple[str, bool], tuple[str, str]] = {}
    for key in dict.fromkeys(zip(notes, df["exclude"])):
        labels[key] = label_note(key[0], bool(key[1]), llm)
    pairs = [labels[(n, bool(e))] for n, e in zip(notes, df["exclude"])]
    df["cause_label"] = [p[0] for p in pairs]
    df["label_source"] = [p[1] for p in pairs]

    df["ticket_id"] = df["case_enquiry_id"].str.strip()
    df["text"] = df["case_title"].map(normalize_text)
    hood = df["neighborhood"].map(normalize_text)
    df["neighborhood"] = hood.where(hood != "", "Unknown")
    df["cell_id"] = [cell_id(la, lo) for la, lo in zip(df["lat"], df["lon"])]
    df["ej_flag"] = points_in_area(ej_area, df["lat"].to_numpy(), df["lon"].to_numpy())
    df["storm_day"] = None
    df["duplicate_of"] = None

    out = df.loc[:, list(REPORT_COLUMNS + EXTRA_COLUMNS)]
    out = out.sort_values("ticket_id", kind="stable").reset_index(drop=True)
    assert len(out) + sum(drops.values()) == len(raw), "row accounting mismatch"
    return out, drops
