# Build log: B (model, backtest, rain trend)

- Kiro did well: built spec 02-risk-model-backtest and model/ with the 3 required Hypothesis property tests (no future data, identical rankings, hit rates in [0, 1]); 10 tests passing. It found that the Logan rain file repeats rain in special reports and duplicate rows (2023-07-29: 2.61 in raw, 1.89 in after dedupe; 2 false storm days removed), kept backtest training storms from overlapping the held-out storm's 2-day report window, and left storms after the last report day (2026-06-23) out of training so they do not become false "no clog" examples.
- I corrected: kept the model to the spec's seven features (no extra interaction features). Known limit: rain_in, high_tide and leaf_season are the same for every cell on a day, so they raise all scores equally and do not change the ranking; the order comes from each cell's report history. The intercept is returned as base_rate so contributions sum exactly to risk_score.

## Numbers (python -m model.run)

- Rain: 5,412 days (2011-12-31 to 2026-10-24); 143 storm days (>= 1.0 in at Logan).
- Tide: threshold 12.177 ft MLLW (95th percentile of daily max); 19 storm days with a high tide.
- Rain trend: +0.9 heavy-rain days per decade (full years 2012-2025); 2026 is partial.
- Final model: 138 storms through 2026-03-16, 1,216,884 (storm, cell) rows, 420 positive. Largest coefficient: past_total_reports (+0.50 per SD); rain_in +0.003.
- Backtest (3 storms since 2023, 8,818 cells, 40 fixable reports):

| Storm | Reports | Model @100 / @200 | Random | Most complaints |
|---|---|---|---|---|
| 2023-07-29 | 12 | 16.7% / 33.3% | 1.2% / 2.1% | 16.7% / 25.0% |
| 2023-08-18 | 11 | 9.1% / 27.3% | 1.0% / 2.4% | 9.1% / 9.1% |
| 2024-01-09 | 17 | 29.4% / 47.1% | 1.1% / 2.4% | 11.8% / 17.6% |
| Pooled | 40 | 20.0% / 37.5% | 1.1% / 2.3% | 12.5% / 17.5% |

  Small sample: treat the gap over most complaints as encouraging, not proven.
- `python -m model.run --quick`: one storm in about 3 s, writes no files.
