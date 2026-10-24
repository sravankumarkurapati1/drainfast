"""Spec 01-ingest-and-labels: row cleaning, drop accounting and Report validity."""
import pandas as pd
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from contracts.cells import cell_id
from contracts.schemas import Report
from data_pipeline.handcheck import has_human_labels, sample_hand_check, score_hand_check
from data_pipeline.ingest import DROP_REASONS, REPORT_COLUMNS, clean_reports
from data_pipeline.run import _to_python, validate_with_contracts

COLUMNS = ["case_enquiry_id", "open_dt", "closed_dt", "case_status", "closure_reason",
           "case_title", "latitude", "longitude", "neighborhood", "location"]


def raw_row(i: int, **kw: str) -> dict[str, str]:
    row = {
        "case_enquiry_id": str(1000 + i), "open_dt": "2024-01-09 08:00:00",
        "closed_dt": "2024-01-10 09:30:00.12", "case_status": "Closed",
        "closure_reason": "Case Closed. Closed date : 2024-01-10 09:30:00.12 Case Resolved Cleaned CB",
        "case_title": "Catchbasin", "latitude": "42.33", "longitude": "-71.07",
        "neighborhood": "Roxbury", "location": "10 Main St  Roxbury  MA  02119",
    }
    row.update(kw)
    return row


ROWS = st.fixed_dictionaries({
    "latitude": st.sampled_from(["42.31", "", "abc", "nan", "42.35"]),
    "longitude": st.sampled_from(["-71.06", "", "-71.1"]),
    "location": st.sampled_from(["5 Elm St", "1 City Hall Plz  Boston  MA  02108", "INTERSECTION of A &amp; B"]),
    "open_dt": st.sampled_from(["2024-01-09 08:00:00", "2024-01-09T08:00:00.123456", "garbage", "",
                                "2023-11-05 01:30:00", "2024-03-10 02:30:00"]),
    "case_status": st.sampled_from(["Closed", "Open", "Pending"]),
    "closed_dt": st.sampled_from(["", "2024-01-10 09:30:00.12", "2020-01-01 00:00:00"]),
    "closure_reason": st.sampled_from(["", "Case Closed Case Resolved", "Case Closed Case Invalid test",
                                       "Case Closed Case Resolved cleaned cb, takes water", "Case Closed Resolved jet"]),
    "neighborhood": st.sampled_from(["", "Dorchester"]),
})


# Feature: 01-ingest-and-labels, Property 3: rows are dropped only for logged reasons,
# kept + dropped = input, and every kept row is a valid Report
@settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
@given(rows=st.lists(ROWS, min_size=1, max_size=12))
def test_drops_are_accounted_for(rows: list[dict[str, str]]) -> None:
    raw = pd.DataFrame([raw_row(i, **r) for i, r in enumerate(rows)], columns=COLUMNS)
    out, drops = clean_reports(raw)
    assert set(drops) <= set(DROP_REASONS)
    assert len(out) + sum(drops.values()) == len(raw)
    assert set(out["ticket_id"]) <= set(raw["case_enquiry_id"])
    validate_with_contracts(out)
    assert set(out["cause_label"]) <= {"clogged_basin", "grading_capacity", "coastal_tide", "unclear"}
    assert out.loc[out["status"] == "open", "closed_at"].isna().all()


def test_clean_reports_fields() -> None:
    raw = pd.DataFrame([
        raw_row(0),
        raw_row(1, latitude=""),
        raw_row(2, location="1 City Hall Plz  Boston  MA  02108"),
        raw_row(3, case_status="Open", closed_dt="", closure_reason="", neighborhood=""),
        raw_row(4, closure_reason="Case Closed Case Invalid test"),
        raw_row(5, case_title="Roadway Flooding &amp; ice"),
    ], columns=COLUMNS)
    out, drops = clean_reports(raw)
    assert dict(drops) == {"missing_coordinates": 1, "city_hall_placeholder": 1}
    assert list(out.columns[: len(REPORT_COLUMNS)]) == list(REPORT_COLUMNS)
    r0 = out.set_index("ticket_id").loc["1000"]
    assert r0["cause_label"] == "clogged_basin" and r0["closing_note"] == "Cleaned CB"
    assert r0["cell_id"] == cell_id(42.33, -71.07)
    assert str(r0["opened_at"].tz) == "America/New_York" and r0["opened_at"].hour == 8
    r3 = out.set_index("ticket_id").loc["1003"]
    assert r3["note_blank"] and r3["neighborhood"] == "Unknown" and pd.isna(r3["closed_at"])
    assert bool(out.set_index("ticket_id").loc["1004", "exclude"])
    assert out.set_index("ticket_id").loc["1005", "text"] == "Roadway Flooding & ice"
    assert validate_with_contracts(out)
    assert Report.model_validate(out.iloc[0][list(REPORT_COLUMNS)].map(_to_python).to_dict()).ticket_id == "1000"


def test_hand_check_sample_and_score() -> None:
    raw = pd.DataFrame([raw_row(i, closure_reason=f"Case Closed Case Resolved cleaned cb {i}") for i in range(80)]
                       + [raw_row(100, closure_reason="")], columns=COLUMNS)
    out, _ = clean_reports(raw)
    sample = sample_hand_check(out)
    assert len(sample) == 50 and not has_human_labels(sample)
    assert sample.equals(sample_hand_check(out))  # seed 42 is deterministic
    assert "1100" not in set(sample["ticket_id"])  # blank notes are never sampled
    sample.loc[:39, "human_label"] = "clogged_basin"
    sample.loc[40:44, "human_label"] = "unclear"
    result = score_hand_check(sample)
    assert result["overall"] == {"n": 45, "correct": 40, "accuracy": round(40 / 45, 4)}
    assert result["n_unfilled"] == 5 and has_human_labels(sample)
