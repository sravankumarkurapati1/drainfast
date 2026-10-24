"""Property and unit tests for model/ (spec 02-risk-model-backtest). All synthetic, offline."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from contracts.schemas import BacktestResult
from model.backtest import hit_rate, random_hit_rates
from model.features import FEATURES, build_features, prepare_reports
from model.service import BASE_RATE, score_cells
from model.storms import build_storm_table, daily_rain, hourly_totals
from model.train import fit_model, trainable_storms

CELLS = [f"c_{i}_{j}" for i in range(3) for j in range(3)]
START = date(2020, 1, 1)
SPAN_DAYS = 900


def make_reports(rows: list[tuple[int, int, bool]]) -> pd.DataFrame:
    """Build prepared reports from (cell index, day offset, fixable) tuples."""
    raw = pd.DataFrame({
        "ticket_id": [f"t{i:05d}" for i in range(len(rows))],
        "cell_id": [CELLS[c] for c, _, _ in rows],
        "opened_at": [pd.Timestamp(START + timedelta(days=d)).tz_localize("America/New_York") + pd.Timedelta(hours=10)
                      for _, d, _ in rows],
        "cause_label": ["clogged_basin" if f else "unclear" for _, _, f in rows],
    })
    return prepare_reports(raw)


report_rows = st.lists(
    st.tuples(st.integers(0, len(CELLS) - 1), st.integers(0, SPAN_DAYS), st.booleans()), max_size=60
)
as_of_offsets = st.integers(1, SPAN_DAYS)


def synthetic_bundle() -> dict:
    """A small fitted model: label depends on past_total_reports so coefficients are non-zero."""
    rng = np.random.default_rng(42)
    n = 400
    training = pd.DataFrame({name: rng.normal(size=n) for name in FEATURES})
    training["label"] = (training["past_total_reports"] + rng.normal(scale=0.5, size=n) > 0).astype(int)
    training["storm_day"] = [START + timedelta(days=i % 20) for i in range(n)]
    return fit_model(training)


BUNDLE = synthetic_bundle()


# Feature: 02-risk-model-backtest, Property 1: no future data
@settings(max_examples=100, deadline=None)
@given(past=report_rows, future=report_rows, offset=as_of_offsets,
       rain=st.floats(0, 10, allow_nan=False), tide=st.booleans())
def test_future_reports_never_change_features(past, future, offset, rain, tide):
    as_of = START + timedelta(days=offset)
    before = [(c, d % offset, f) for c, d, f in past]          # strictly before as_of
    after = [(c, offset + d, f) for c, d, f in future]          # on or after as_of
    base = build_features(as_of, rain, tide, reports=make_reports(before), cell_ids=CELLS)
    more = build_features(as_of, rain, tide, reports=make_reports(before + after), cell_ids=CELLS)
    pd.testing.assert_frame_equal(base, more)


# Feature: 02-risk-model-backtest, Property 2: identical inputs give identical rankings
@settings(max_examples=100, deadline=None)
@given(rows=report_rows, offset=as_of_offsets, rain=st.floats(0, 10, allow_nan=False),
       tide=st.booleans(), seed=st.integers(0, 2**32 - 1))
def test_identical_inputs_give_identical_rankings(rows, offset, rain, tide, seed):
    as_of = START + timedelta(days=offset)
    reports = make_reports(rows)
    shuffled = reports.sample(frac=1.0, random_state=seed % (2**32)).reset_index(drop=True)
    cells_shuffled = list(np.random.default_rng(seed).permutation(CELLS))
    first = score_cells(as_of, rain, tide, bundle=BUNDLE, reports=reports, cell_ids=CELLS)
    second = score_cells(as_of, rain, tide, bundle=BUNDLE, reports=shuffled, cell_ids=cells_shuffled)
    pd.testing.assert_frame_equal(first, second)
    scores = first["risk_score"].to_numpy()
    assert np.all(scores[:-1] >= scores[1:])


# Feature: 02-risk-model-backtest, Property 3: hit rates are between 0 and 1
@settings(max_examples=100, deadline=None)
@given(ranking=st.permutations(CELLS), report_cells=st.lists(st.sampled_from(CELLS), max_size=30),
       top_n=st.integers(0, 2 * len(CELLS)))
def test_hit_rates_between_zero_and_one(ranking, report_cells, top_n):
    rate = hit_rate(ranking, report_cells, top_n)
    assert 0.0 <= rate <= 1.0
    rand = random_hit_rates(CELLS, report_cells, top_ns=(3, 6), n_rankings=20)
    assert all(0.0 <= v <= 1.0 for v in rand.values())
    assert rand[3] <= rand[6]


@settings(max_examples=50, deadline=None)
@given(rows=report_rows, offset=as_of_offsets, rain=st.floats(0, 10, allow_nan=False), tide=st.booleans())
def test_contributions_sum_to_risk_score(rows, offset, rain, tide):
    scored = score_cells(START + timedelta(days=offset), rain, tide, bundle=BUNDLE,
                         reports=make_reports(rows), cell_ids=CELLS)
    parts = scored[[f"{n}_contribution" for n in FEATURES]].sum(axis=1) + scored[BASE_RATE]
    assert np.allclose(parts, scored["risk_score"], atol=1e-9, rtol=0)


def test_feature_values_on_a_small_example():
    reports = make_reports([(0, 10, True), (0, 300, True), (0, 305, False), (1, 400, True)])
    feats = build_features(START + timedelta(days=400), 1.2, True, reports=reports, cell_ids=CELLS)
    c0 = feats.set_index("cell_id").loc[CELLS[0]]
    assert c0["past_fixable_count"] == 2 and c0["past_fixable_365d"] == 1
    assert c0["past_total_reports"] == 3 and c0["days_since_last_fixable"] == 100
    c1 = feats.set_index("cell_id").loc[CELLS[1]]          # its only report is on as_of itself
    assert c1["past_total_reports"] == 0 and c1["days_since_last_fixable"] == 3650
    assert set(feats.columns) == {"cell_id", *FEATURES}


def test_special_reports_are_not_double_counted():
    times = pd.to_datetime(["2023-07-29 14:20", "2023-07-29 14:54", "2023-07-29 15:54"]).tz_localize("UTC")
    hourly = hourly_totals(pd.DataFrame({"valid_utc": times, "p": [0.30, 0.50, 0.20]}))
    assert hourly["p"].tolist() == [0.50, 0.20]


def test_storm_day_threshold_is_inclusive():
    daily = pd.DataFrame({"storm_day": [date(2024, 1, 9), date(2024, 1, 10)],
                          "rain_total_in": [1.0, 0.99], "max_hourly_in": [0.4, 0.3]})
    storms = build_storm_table(daily, {date(2024, 1, 9)})
    assert storms["is_storm_day"].tolist() == [True, False]
    assert storms["high_tide_flag"].tolist() == [True, False]


def test_daily_rain_uses_local_days_across_dst():
    times = pd.to_datetime(["2012-11-04 05:54", "2012-11-04 06:54", "2012-11-05 04:54"]).tz_localize("UTC")
    hourly = hourly_totals(pd.DataFrame({"valid_utc": times, "p": [0.1, 0.2, 0.3]}))
    daily = daily_rain(hourly)
    assert daily["storm_day"].tolist() == [date(2012, 11, 4)]
    assert daily["rain_total_in"].tolist() == [0.6]


def test_training_storms_never_overlap_the_held_out_storm():
    storms = pd.DataFrame({"storm_day": [START + timedelta(days=d) for d in (100, 198, 199, 200)],
                           "is_storm_day": True})
    reports = make_reports([(0, 500, True)])
    held_out = START + timedelta(days=200)
    days = trainable_storms(storms, reports, before=held_out)
    assert days == [START + timedelta(days=100)]          # 198 and 199 windows reach day 200


def test_backtest_result_rejects_out_of_range_rates():
    with pytest.raises(Exception):
        BacktestResult(storm_day=START, n_fixable_reports=1, n_cells=9, hit_rate_top100=1.5, hit_rate_top200=1.5,
                       random_top100=0, random_top200=0, most_complaints_top100=0, most_complaints_top200=0)
