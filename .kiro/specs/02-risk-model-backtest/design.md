# Design Document: 02-risk-model-backtest

## Overview

```
logan_hourly_precip.csv ─ storms.py ─┐
boston_tide_hourly.csv ── tide.py ───┼─> storms.parquet, tide_threshold.json
                                     └─ trend.py ─> rain_trend.json
reports.parquet, cells.parquet ─ features.py ─ train.py ─> model.joblib
                                              └ backtest.py ─> backtest.json
service.py: score_cells(as_of, rain_in, high_tide)   (used by backend/priority.py)
```

## Components

| Module | Responsibility |
|---|---|
| `paths.py` | Output paths. Shared paths come from `data_pipeline.paths` until `contracts/paths.py` exists. |
| `storms.py` | Hourly periods (dedupe specials), local daily totals, storm table, Storm validation. |
| `tide.py` | Daily max, 95th percentile threshold, high-tide days. |
| `trend.py` | Heavy-rain days per year, partial year, slope per decade. |
| `features.py` | `prepare_reports`, `build_features` (pure when reports and cells are passed). |
| `train.py` | Label window, trainable storms, training set, `fit_model`. |
| `service.py` | `score_cells`, contributions with `base_rate`, deterministic ranking. |
| `backtest.py` | Storm choice, hit rate, random and most-complaints baselines, table. |
| `run.py` | CLI; `--quick` backtests one storm and writes nothing. |

## Decisions

- **One reading per hourly period.** ASOS special reports and duplicate rows repeat rain
  already in the routine :54 report. Summing every row inflated some days (2023-07-29:
  2.61 in raw, 1.89 in after dedupe) and turned 2 non-storm days into storm days.
- **Hours are keyed in UTC**, then converted, so the November fall-back hour is not
  ambiguous.
- **Tide time is local station time.** The spring-forward hour is a blank row, which
  only happens with local time, so the date is read straight from `t`.
- **No leakage in training labels.** For held-out storm S, a training storm S' qualifies
  only when S' + 2 days < S; otherwise its label window would include S's reports.
- **No false zeros.** Storms whose label window passes the last report day
  (2026-06-23) are left out of training.
- **base_rate.** The intercept is returned as its own term so the parts sum exactly to
  risk_score. It is not a feature.
- **--quick writes nothing**, so it cannot overwrite the full 3-storm backtest.
- **Known limits.** rain_in, high_tide and leaf_season are the same for every cell on a
  given day, so they shift all scores equally and do not change the ranking; the order
  comes from the four report-history features. The saved model was trained on all
  storms, so `score_cells` for a past storm date has seen that storm; only the
  backtest numbers are out-of-sample. The tide threshold uses the whole tide record.

## Testing strategy

Hypothesis (`tests/model/test_model.py`): future reports never change features;
identical (and reordered) inputs give identical rankings; hit rates stay in [0, 1];
contributions sum to risk_score. Unit tests: feature values on a small example, special
reports not double counted, inclusive 1.0 inch threshold, local days across DST,
training storms never overlap the held-out storm.
