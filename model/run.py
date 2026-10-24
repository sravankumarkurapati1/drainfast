"""Build storm days, tide threshold, rain trend, the risk model and the backtest.

Usage:
    python -m model.run          # write all outputs to data/demo/
    python -m model.run --quick  # backtest one storm and print it; writes no files
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

import joblib
import pandas as pd

from contracts.schemas import STORM_DAY_THRESHOLD_IN
from model import paths
from model.backtest import backtest_storm, choose_backtest_storms, format_table
from model.features import load_cell_ids, load_reports
from model.storms import build_storm_table, daily_rain, hourly_totals, load_hourly_rain, validate_storms
from model.tide import high_tide_days, load_daily_max, threshold_record, tide_threshold
from model.train import train, trainable_storms
from model.trend import rain_trend

log = logging.getLogger("model")


def build_storms() -> tuple[pd.DataFrame, dict]:
    """Return the daily storm table and the tide threshold record."""
    daily = daily_rain(hourly_totals(load_hourly_rain(paths.RAIN_PATH)))
    tide_max = load_daily_max(paths.TIDE_PATH)
    threshold = tide_threshold(tide_max)
    storms = build_storm_table(daily, high_tide_days(tide_max, threshold), STORM_DAY_THRESHOLD_IN)
    validate_storms(storms)
    return storms, threshold_record(tide_max, threshold)


def write_json(path, payload) -> None:
    """Write payload as indented UTF-8 JSON."""
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="backtest one storm only; write no files")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    start = time.perf_counter()

    storms, tide_info = build_storms()
    reports = load_reports()
    cell_ids = load_cell_ids(reports=reports)
    n_storm = int(storms["is_storm_day"].sum())
    print("\n=== DrainFast model ===")
    print(f"days of rain data:  {len(storms)} ({storms['storm_day'].min()} to {storms['storm_day'].max()})")
    print(f"storm days:         {n_storm} (>= {STORM_DAY_THRESHOLD_IN} in at Logan)")
    print(f"tide threshold:     {tide_info['threshold_ft']} ft MLLW (95th percentile of daily max)")
    print(f"high-tide storms:   {int((storms['is_storm_day'] & storms['high_tide_flag']).sum())}")
    print(f"reports used:       {len(reports)} ({int(reports['fixable'].sum())} clogged_basin), "
          f"last report day {reports['day'].max().date()}")
    print(f"cells ranked:       {len(cell_ids)}")

    backtest_days = choose_backtest_storms(storms, reports)
    if args.quick:
        backtest_days = backtest_days[:1]
    rows = [backtest_storm(day, storms, reports, cell_ids) for day in backtest_days]
    print("\nBacktest (hit rate = share of the storm's clogged_basin reports in the top N cells)")
    print(format_table(rows))

    if args.quick:
        print(f"\nquick run: {time.perf_counter() - start:.1f} s; no files written")
        return 0

    train_days = trainable_storms(storms, reports)
    bundle = train(train_days, storms, reports, cell_ids)
    paths.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    storms.to_parquet(paths.STORMS_PATH, index=False)
    write_json(paths.TIDE_THRESHOLD_PATH, tide_info)
    trend = rain_trend(storms, STORM_DAY_THRESHOLD_IN)
    write_json(paths.RAIN_TREND_PATH, trend)
    write_json(paths.BACKTEST_PATH, [r.model_dump(mode="json") for r, _ in rows])
    joblib.dump(bundle, paths.MODEL_PATH)

    logreg = bundle["pipeline"].named_steps["logreg"]
    print(f"\nfinal model: {len(train_days)} storms through {bundle['trained_through']}, "
          f"{bundle['n_rows']} rows, {bundle['n_positive']} positive")
    print("coefficients (per standard deviation):")
    for name, coef in zip(bundle["features"], logreg.coef_[0]):
        print(f"  {name:24} {coef:+.3f}")
    print(f"  {'base_rate (intercept)':24} {logreg.intercept_[0]:+.3f}")
    print(f"rain trend: slope {trend['slope_per_decade']} heavy-rain days per decade "
          f"(full years {trend['slope_years']}), partial year {trend['partial_year']}")
    for p in (paths.STORMS_PATH, paths.TIDE_THRESHOLD_PATH, paths.RAIN_TREND_PATH, paths.BACKTEST_PATH, paths.MODEL_PATH):
        print(f"wrote {p.relative_to(paths.PROJECT_ROOT)}")
    print(f"done in {time.perf_counter() - start:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
