"""Build data/demo/reports.parquet and the hand check; score a filled hand check.

Usage:
    python -m data_pipeline.run            # build reports and hand_check.csv
    python -m data_pipeline.run --score    # score data/demo/hand_check.csv
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from data_pipeline import paths
from data_pipeline.geo import load_polygons
from data_pipeline.handcheck import has_human_labels, sample_hand_check, score_hand_check
from data_pipeline.ingest import DROP_REASONS, EXTRA_COLUMNS, REPORT_COLUMNS, clean_reports, load_raw
from data_pipeline.llm import make_labeler

log = logging.getLogger("data_pipeline")

REPORTS_SCHEMA = pa.schema([
    ("ticket_id", pa.string()),
    ("opened_at", pa.timestamp("us", tz="America/New_York")),
    ("closed_at", pa.timestamp("us", tz="America/New_York")),
    ("status", pa.string()),
    ("lat", pa.float64()),
    ("lon", pa.float64()),
    ("cell_id", pa.string()),
    ("text", pa.string()),
    ("closing_note", pa.string()),
    ("note_blank", pa.bool_()),
    ("cause_label", pa.string()),
    ("label_source", pa.string()),
    ("storm_day", pa.date32()),
    ("neighborhood", pa.string()),
    ("ej_flag", pa.bool_()),
    ("duplicate_of", pa.string()),
    ("exclude", pa.bool_()),
])


def _to_python(value: object) -> object:
    """Convert pandas and numpy scalars to plain Python values for Pydantic."""
    if value is None or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


def validate_with_contracts(reports: pd.DataFrame) -> bool:
    """Validate every row as contracts.schemas.Report when that module exists.

    Returns True when validated, False when contracts.schemas is not available yet.
    Raises ValueError naming the first invalid ticket.
    """
    try:
        from contracts.schemas import Report  # type: ignore[import-not-found]
    except ImportError:
        log.warning("contracts.schemas not found yet; skipped Report validation.")
        return False
    for row in reports.loc[:, list(REPORT_COLUMNS)].to_dict("records"):
        record = {k: _to_python(v) for k, v in row.items()}
        try:
            Report.model_validate(record)
        except Exception as exc:
            raise ValueError(f"ticket {record['ticket_id']} is not a valid Report: {exc}") from exc
    return True


def write_reports(reports: pd.DataFrame) -> None:
    """Write reports.parquet with an explicit, stable schema."""
    paths.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(
        reports.loc[:, list(REPORT_COLUMNS + EXTRA_COLUMNS)], schema=REPORTS_SCHEMA, preserve_index=False
    )
    pq.write_table(table, paths.REPORTS_PATH)


def write_hand_check(reports: pd.DataFrame) -> str:
    """Write hand_check.csv unless a human already started filling it in."""
    if paths.HAND_CHECK_PATH.exists():
        existing = pd.read_csv(paths.HAND_CHECK_PATH, dtype=str, keep_default_na=False)
        if has_human_labels(existing):
            return "kept existing file (human labels already filled)"
    sample_hand_check(reports).to_csv(paths.HAND_CHECK_PATH, index=False)
    return "written"


def print_summary(raw_rows: int, reports: pd.DataFrame, drops: Counter[str], validated: bool,
                  llm_calls: int, hand_check: str) -> None:
    """Print the run summary: kept and dropped rows, blank notes, labels and sources."""
    print("\n=== DrainFast data pipeline: reports ===")
    print(f"input rows:        {raw_rows}")
    print(f"kept rows:         {len(reports)}")
    print(f"dropped rows:      {sum(drops.values())}")
    for reason in DROP_REASONS:
        print(f"  {reason:22} {drops.get(reason, 0)}")
    print(f"blank crew notes:  {int(reports['note_blank'].sum())}")
    print(f"excluded notes:    {int(reports['exclude'].sum())}")
    print("cause_label:")
    for label, n in reports["cause_label"].value_counts().sort_index().items():
        print(f"  {label:22} {n}")
    print("label_source:")
    for src, n in reports["label_source"].value_counts().sort_index().items():
        print(f"  {src:22} {n}")
    print(f"LLM calls:         {llm_calls}")
    print(f"Report validation: {'passed' if validated else 'skipped (contracts.schemas missing)'}")
    print(f"hand_check.csv:    {hand_check}")
    print(f"wrote {paths.REPORTS_PATH.relative_to(paths.PROJECT_ROOT)}")


def build() -> int:
    """Build reports.parquet and hand_check.csv from the raw 311 export."""
    raw = load_raw(paths.RAW_311_PATH)
    ej_area = load_polygons(paths.RAW_EJ_PATH) if paths.RAW_EJ_PATH.exists() else None
    if ej_area is None:
        log.warning("EJ file missing; ej_flag is False for every report.")
    labeler = make_labeler(paths.LLM_CACHE_PATH)
    reports, drops = clean_reports(raw, ej_area=ej_area, llm=labeler)
    validated = validate_with_contracts(reports)
    write_reports(reports)
    if labeler is not None:
        labeler.save_cache()
    hand_check = write_hand_check(reports)
    print_summary(len(raw), reports, drops, validated, labeler.calls if labeler else 0, hand_check)
    return 0


def score() -> int:
    """Score the filled hand check and write label_accuracy.json."""
    if not paths.HAND_CHECK_PATH.exists():
        print(f"{paths.HAND_CHECK_PATH} not found. Run `make data` first.", file=sys.stderr)
        return 1
    df = pd.read_csv(paths.HAND_CHECK_PATH, dtype=str, keep_default_na=False)
    try:
        result = score_hand_check(df)
    except ValueError as exc:
        print(f"hand check: {exc}", file=sys.stderr)
        return 1
    paths.LABEL_ACCURACY_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    o = result["overall"]
    print(f"label accuracy: {o['correct']}/{o['n']} = {o['accuracy']}")
    for src, r in result["by_label_source"].items():
        print(f"  {src:6} {r['correct']}/{r['n']} = {r['accuracy']}")
    print(f"wrote {paths.LABEL_ACCURACY_PATH.relative_to(paths.PROJECT_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score", action="store_true", help="score data/demo/hand_check.csv")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return score() if args.score else build()


if __name__ == "__main__":
    sys.exit(main())
