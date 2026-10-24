"""Hypothesis strategies for backend property tests: random cells and 311 reports."""
from datetime import datetime, timedelta, timezone

from hypothesis import strategies as st

from contracts.cells import cell_center
from contracts.schemas import BasinOwner, CauseLabel, Cell, LabelSource, Report, ReportStatus

CELL_IDS = [f"c_{100 + i}_{100 + 2 * i}" for i in range(8)]
NEIGHBORHOODS = ["East Boston", "Dorchester", "Roxbury", "Jamaica Plain"]
START = datetime(2015, 1, 1, tzinfo=timezone(timedelta(hours=-5)))


@st.composite
def cells(draw: st.DrawFn) -> list[Cell]:
    out = []
    for cid in CELL_IDS:
        lat, lon = cell_center(cid)
        out.append(Cell(cell_id=cid, lat=lat, lon=lon, neighborhood=draw(st.sampled_from(NEIGHBORHOODS)),
                        basin_count=draw(st.integers(0, 12)), basin_owner=draw(st.sampled_from(list(BasinOwner))),
                        ej_flag=draw(st.booleans()), flood_area_flag=draw(st.booleans())))
    return out


@st.composite
def report(draw: st.DrawFn, ticket_id: str) -> Report:
    cid = draw(st.sampled_from(CELL_IDS))
    lat, lon = cell_center(cid)
    opened = START + timedelta(minutes=draw(st.integers(0, 60 * 24 * 365 * 11)))
    is_open = draw(st.booleans())
    note_blank = draw(st.booleans())
    return Report(ticket_id=ticket_id, opened_at=opened,
                  closed_at=None if is_open else opened + timedelta(hours=draw(st.integers(0, 500))),
                  status=ReportStatus.open if is_open else ReportStatus.closed, lat=lat, lon=lon, cell_id=cid,
                  text="Catchbasin", closing_note=None if note_blank else "crew note", note_blank=note_blank,
                  cause_label=draw(st.sampled_from(list(CauseLabel))), label_source=LabelSource.rule,
                  neighborhood=draw(st.sampled_from(NEIGHBORHOODS)), ej_flag=draw(st.booleans()))


@st.composite
def reports(draw: st.DrawFn, min_size: int = 1, max_size: int = 40) -> list[Report]:
    n = draw(st.integers(min_size, max_size))
    return [draw(report(ticket_id=f"1010{i:08d}")) for i in range(n)]
