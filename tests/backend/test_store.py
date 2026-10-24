"""store.py must accept pipeline files that carry extra, non-contract columns."""
import json

import pandas as pd

from backend import store
from backend.paths import FIXTURES_DIR


def _fixture_frame(name: str) -> pd.DataFrame:
    # Read as plain objects so ticket IDs stay strings, as in the pipeline's parquet.
    return pd.DataFrame(json.loads((FIXTURES_DIR / name).read_text()))


def test_extra_columns_are_ignored_and_excluded_rows_dropped(empty_demo_dir):
    reports = _fixture_frame("report.json")
    reports["opened_at"] = pd.to_datetime(reports["opened_at"], utc=True).dt.tz_convert("America/New_York")
    reports["closed_at"] = pd.to_datetime(reports["closed_at"], utc=True).dt.tz_convert("America/New_York")
    reports["exclude"] = [False] * (len(reports) - 1) + [True]
    reports.to_parquet(empty_demo_dir / "reports.parquet")

    cells = _fixture_frame("cell.json")
    cells["bwsc_share"] = 1.0
    cells.to_parquet(empty_demo_dir / "cells.parquet")

    loaded_reports, r_fixture = store.load_reports()
    loaded_cells, c_fixture = store.load_cells()
    assert not r_fixture and len(loaded_reports) == len(reports) - 1
    assert not c_fixture and len(loaded_cells) == len(cells)
