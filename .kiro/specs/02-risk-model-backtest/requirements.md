# Requirements Document: 02-risk-model-backtest

## Introduction

Member B's spec. `python -m model.run` writes `data/demo/storms.parquet`,
`data/demo/tide_threshold.json`, `data/demo/rain_trend.json`, `data/demo/backtest.json`
and `data/demo/model.joblib`. `python -m model.run --quick` backtests one storm in under
30 seconds and writes no files. It runs after `make data` and `make cells`.

## Requirements

### Requirement 1: Storm days

1. THE builder SHALL read `data/raw/rain/logan_hourly_precip.csv` (station, valid,
   p01i). `valid` is UTC; p01i values M and T SHALL count as 0.
2. Each hourly accumulation period SHALL be counted once: special reports and exact
   duplicate rows inside the same period (previous :54, this :54] SHALL not be added
   to the routine report. The period total is the largest reading in it.
3. Hours SHALL be converted to America/New_York and summed by local day, giving
   `rain_total_in` and `max_hourly_in` per day. Daylight saving time SHALL not fail.
4. A storm day SHALL have `rain_total_in` of 1.0 inch or more
   (`contracts.schemas.STORM_DAY_THRESHOLD_IN`), inclusive.
5. `storms.parquet` SHALL hold every day: the `contracts.schemas.Storm` fields plus
   `is_storm_day`, and every row SHALL validate as a Storm.

### Requirement 2: Tide

1. THE builder SHALL read `data/raw/tide/boston_tide_hourly.csv` (t = local station
   time, v = water level in feet above MLLW) and drop rows without a level.
2. The threshold SHALL be the 95th percentile of daily maximum levels, saved to
   `tide_threshold.json` with the percentile, datum, station and date range.
3. A day's `high_tide_flag` SHALL be true when its daily maximum is above the threshold,
   and false when there is no tide data for the day.

### Requirement 3: Rain trend

1. Per year, THE builder SHALL count days with 1.0 inch or more.
2. A final year without data through December 31 SHALL be kept and named in
   `partial_year`; a leading year that does not start on January 1 SHALL be dropped.
3. The linear slope per decade SHALL use full years only.
4. `rain_trend.json` SHALL hold `points` (`contracts.schemas.RainTrendPoint` items),
   `slope_per_decade`, `partial_year`, `threshold_in`, `station` and `slope_years`.

### Requirement 4: Reports and target

1. Reports SHALL come from `data/demo/reports.parquet`, or
   `contracts/fixtures/report.json` when it is missing. Rows with `exclude` true or a
   `duplicate_of` value SHALL be dropped.
2. A report SHALL belong to storm S when opened (local date) on S or within 2 days after.
3. The target SHALL be 1 when a cell has at least one `clogged_basin` report for S.

### Requirement 5: Features

1. `model/features.py` `build_features(as_of, rain_in, high_tide)` SHALL return one row
   per cell from `cells.parquet` with exactly: `past_fixable_count`,
   `past_fixable_365d`, `past_total_reports`, `days_since_last_fixable` (capped at 3650,
   and 3650 when there is none), `leaf_season` (October or November), `rain_in`,
   `high_tide`.
2. Features SHALL use ONLY reports opened strictly before as_of's local date and
   SHALL never read today's date.

### Requirement 6: Model and service

1. THE model SHALL be logistic regression on standardized features, class_weight
   balanced, random_state 42, trained on (storm day, cell) examples.
2. Training SHALL use only storms whose label window ends on or before the last report
   day, so no storm gets false zero labels.
3. `model/service.py` `score_cells(as_of, rain_in, high_tide)` SHALL return per cell the
   `risk_score` (log-odds), each feature value and one `<feature>_contribution`
   (coefficient x standardized value), plus `base_rate` (the intercept), sorted by
   risk_score then cell_id.
4. `risk_score` SHALL equal `base_rate` plus the feature contributions, so the backend
   can build a priority score whose factors sum exactly (tech.md rule 10).

### Requirement 7: Backtest

1. THE backtest SHALL use the 3 storm days since 2023-01-01 with the most
   `clogged_basin` reports (ties to the earlier day), among storms fully covered by
   report data.
2. For each storm S, the model SHALL be retrained using only storms whose label window
   ends strictly before S.
3. Hit rate at top 100 and top 200 SHALL be the share of S's fixable reports whose cell
   is in the top N.
4. Baselines: random (average of 200 rankings seeded from 42) and most past complaints
   (rank by `past_total_reports` before S, ties by cell_id).
5. Each result SHALL record `n_fixable_reports` and `n_cells`, validate as
   `contracts.schemas.BacktestResult`, and be written to `backtest.json`. A table SHALL
   be printed even when the model loses to a baseline.

### Requirement 8: Property tests

1. Hypothesis tests SHALL check: adding reports dated on or after as_of never changes
   the features; identical inputs give identical rankings; hit rates are between 0 and 1.
