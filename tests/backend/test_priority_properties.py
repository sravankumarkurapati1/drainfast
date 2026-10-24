"""Property tests for backend/priority.py (spec 03-backend-mcp, Requirement 7)."""
from datetime import date, datetime, timedelta, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.model_adapter import fallback_scores
from backend.priority import build_backlog, build_brief
from contracts.schemas import FACTOR_SUM_TOLERANCE, BriefResponse, ReportStatus
from tests.backend.strategies import cells, report, reports

days = st.dates(min_value=date(2016, 1, 1), max_value=date(2026, 12, 31))
crews = st.integers(1, 4)
capacity = st.integers(1, 40)
rain = st.floats(0.0, 5.0, allow_nan=False)


def _brief(rs, cs, day, n_crews, cap, rain_in, tide=False) -> BriefResponse:
    return build_brief(day, n_crews, cap, rain_in, tide, fallback_scores(rs, day, rain_in), cs, rs, True)


# Feature: 03-backend-mcp, Property 1: priority_score is exactly the sum of its factors
@settings(max_examples=100, deadline=None)
@given(reports(), cells(), days, crews, capacity, rain, st.booleans())
def test_priority_score_equals_sum_of_factors(rs, cs, day, n, cap, r, tide):
    brief = _brief(rs, cs, day, n, cap, r, tide)
    now = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    backlog = build_backlog(now, 50, fallback_scores(rs, day, 0.0), cs, rs)
    for item in [*brief.items, *backlog]:
        assert abs(item.priority_score - sum(f.contribution for f in item.factors)) <= FACTOR_SUM_TOLERANCE


# Feature: 03-backend-mcp, Property 2: every brief item cites tickets from its cell, opened before the date
@settings(max_examples=100, deadline=None)
@given(reports(), cells(), days, crews, capacity, rain)
def test_brief_evidence_from_same_cell_and_past(rs, cs, day, n, cap, r):
    by_id = {x.ticket_id: x for x in rs}
    for item in _brief(rs, cs, day, n, cap, r).items:
        assert item.evidence_ticket_ids
        for tid in item.evidence_ticket_ids:
            assert by_id[tid].cell_id == item.cell_id
            assert by_id[tid].opened_at.date() < day


# Feature: 03-backend-mcp, Property 2b: every backlog item cites at least one ticket, itself first
@settings(max_examples=100, deadline=None)
@given(reports(), cells(), days)
def test_backlog_evidence_every_item(rs, cs, day):
    now = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    items = build_backlog(now, 100, fallback_scores(rs, day, 0.0), cs, rs)
    assert len(items) == sum(r.status == ReportStatus.open for r in rs)
    for it in items:
        assert it.evidence_ticket_ids and it.evidence_ticket_ids[0] == it.ticket_id


# Feature: 03-backend-mcp, Property 3: identical inputs in any order give identical rankings
@settings(max_examples=100, deadline=None)
@given(reports(), cells(), days, crews, capacity, rain, st.randoms(use_true_random=False))
def test_rankings_deterministic_under_shuffle(rs, cs, day, n, cap, r, rnd):
    a = _brief(rs, cs, day, n, cap, r)
    shuffled_r, shuffled_c = rs[:], cs[:]
    rnd.shuffle(shuffled_r)
    rnd.shuffle(shuffled_c)
    b = _brief(shuffled_r, shuffled_c, day, n, cap, r)
    assert a == b


# Feature: 03-backend-mcp, Property 4: reports opened on or after the brief date never change the brief
@settings(max_examples=100, deadline=None)
@given(reports(), cells(), days, crews, capacity, rain, st.data())
def test_future_reports_do_not_change_brief(rs, cs, day, n, cap, r, data):
    base = _brief(rs, cs, day, n, cap, r)
    extra = data.draw(st.lists(report(ticket_id="9"), min_size=1, max_size=5))
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone(timedelta(hours=-5)))
    future = []
    for i, x in enumerate(extra):
        opened = start + timedelta(hours=i * 7)
        future.append(x.model_copy(update={"ticket_id": f"9999{i:08d}", "opened_at": opened,
                                           "closed_at": None if x.closed_at is None else opened}))
    assert _brief(rs + future, cs, day, n, cap, r) == base


# Feature: 03-backend-mcp, Property 5: the brief never exceeds crew capacity
@settings(max_examples=100, deadline=None)
@given(reports(), cells(), days, crews, capacity, rain)
def test_brief_respects_crew_capacity(rs, cs, day, n, cap, r):
    brief = _brief(rs, cs, day, n, cap, r)
    basins = {c.cell_id: max(c.basin_count, 1) for c in cs}
    counted = [basins[i.cell_id] for i in brief.items]
    assert len(brief.items) <= n * cap
    assert sum(counted[:-1]) < n * cap  # every item but the last was added while under capacity
    assert [i.rank for i in brief.items] == list(range(1, len(brief.items) + 1))
