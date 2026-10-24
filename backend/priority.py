"""Priority score, crew brief and backlog (pure functions; no I/O, no clock).

priority_score is always exactly the sum of its FactorContribution items
(tech.md rule 10), and every item cites at least one 311 ticket (product rule 2).
"""
from datetime import date, datetime
from typing import Optional

from backend.config import weights
from backend.model_adapter import CellScore, is_rain_factor
from contracts.cells import cell_center
from contracts.schemas import (STATUS_UNCLEAR, BacklogItem, BasinOwner, BriefItem, BriefResponse,
                               CauseLabel, Cell, FactorContribution, Report, ReportStatus)

BWSC_SHARE = {BasinOwner.BWSC: 1.0, BasinOwner.Mixed: 0.5}


def _day(dt: datetime) -> date:
    """Calendar date of a timestamp in its own time zone."""
    return dt.date()


def cell_factors(cell: Optional[Cell], high_tide: bool) -> list[FactorContribution]:
    """Location factors added on top of the model: EJ, flood area, tide x flood, BWSC share."""
    w = weights()["brief"]
    ej = 1.0 if cell and cell.ej_flag else 0.0
    flood = 1.0 if cell and cell.flood_area_flag else 0.0
    tide_flood = flood * (1.0 if high_tide else 0.0)
    bwsc = BWSC_SHARE.get(cell.basin_owner, 0.0) if cell else 0.0
    return [
        FactorContribution(factor="Environmental justice area", value=ej, contribution=w["ej"] * ej),
        FactorContribution(factor="Inside modeled flood area", value=flood, contribution=w["flood_area"] * flood),
        FactorContribution(factor="High tide in flood area", value=tide_flood,
                           contribution=w["high_tide_flood_area"] * tide_flood),
        FactorContribution(factor="Share of basins run by BWSC", value=bwsc, contribution=w["bwsc_share"] * bwsc),
    ]


def total(factors: list[FactorContribution]) -> float:
    """priority_score: exactly the sum of the factor contributions."""
    return sum(f.contribution for f in factors)


# Factors whose value needs a unit or article to read naturally in a reason sentence.
PHRASES = {"Recent clogged drain": "a recent clogged drain ({v:g} days ago)"}


def _phrase(f: FactorContribution) -> str:
    """'past clogged-drain reports (8)'; yes/no flags without a number; acronyms kept."""
    if f.factor in PHRASES:
        return PHRASES[f.factor].format(v=f.value)
    name = f.factor if f.factor[:2].isupper() else f.factor[0].lower() + f.factor[1:]
    return name if f.value in (0.0, 1.0) and "report" not in name.lower() else f"{name} ({f.value:g})"


def reason_for(factors: list[FactorContribution]) -> str:
    """One plain-language sentence from the two largest positive factors."""
    top = sorted((f for f in factors if f.contribution > 0), key=lambda f: (-f.contribution, f.factor))[:2]
    if not top:
        return "Ranked by past 311 reports at this location."
    parts = [_phrase(f) for f in top]
    return "Ranked high mainly because of " + " and ".join(parts) + "."


def evidence_for(cell_reports: list[Report], before: date, limit: int) -> list[str]:
    """Up to `limit` ticket IDs opened before `before`: newest clogged-drain tickets first,
    otherwise the newest reports."""
    past = sorted((r for r in cell_reports if _day(r.opened_at) < before),
                  key=lambda r: (r.opened_at, r.ticket_id), reverse=True)
    clogged = [r.ticket_id for r in past if r.cause_label == CauseLabel.clogged_basin]
    return (clogged or [r.ticket_id for r in past])[:limit]


def _by_cell(reports: list[Report]) -> dict[str, list[Report]]:
    """Group reports by cell_id."""
    out: dict[str, list[Report]] = {}
    for r in reports:
        out.setdefault(r.cell_id, []).append(r)
    return out


def _lat_lon(cell_id: str, cell: Optional[Cell], reports: list[Report]) -> tuple[float, float]:
    """Map position: the cell record, else the grid center, else the first report."""
    if cell:
        return cell.lat, cell.lon
    try:
        return cell_center(cell_id)
    except (ValueError, IndexError):
        return reports[0].lat, reports[0].lon


def build_brief(day: date, crews: int, capacity_per_crew: int, rain_in: float, high_tide: bool,
                scores: dict[str, CellScore], cells: list[Cell], reports: list[Report],
                fallback_mode: bool) -> BriefResponse:
    """Rank cells and fill crew capacity (basins), skipping cells with no past tickets."""
    max_evidence = int(weights()["brief_defaults"]["max_evidence"])
    cell_map = {c.cell_id: c for c in cells}
    by_cell = _by_cell(reports)
    ranked: list[tuple[float, str, list[FactorContribution], list[str]]] = []
    for cid, cs in scores.items():
        evidence = evidence_for(by_cell.get(cid, []), day, max_evidence)
        if not evidence:
            continue  # product rule 2: no evidence, no item
        # Rain is the same for every location, so it is shown once at the top of the
        # brief (BriefResponse.forecast_rain_in), not as a per-location factor. The
        # model's rain term is a constant shift, so dropping it keeps the ranking.
        factors = [f for f in cs.factors if not is_rain_factor(f)] + cell_factors(cell_map.get(cid), high_tide)
        ranked.append((total(factors), cid, factors, evidence))
    ranked.sort(key=lambda t: (-t[0], t[1]))

    capacity = crews * capacity_per_crew
    items: list[BriefItem] = []
    basins = 0
    for score, cid, factors, evidence in ranked:
        if basins >= capacity or len(items) >= capacity:
            break
        cell = cell_map.get(cid)
        basins += max(cell.basin_count, 1) if cell else 1
        lat, lon = _lat_lon(cid, cell, by_cell.get(cid, []))
        items.append(BriefItem(rank=len(items) + 1, cell_id=cid, lat=lat, lon=lon, priority_score=score,
                               factors=factors, reason=reason_for(factors), evidence_ticket_ids=evidence))
    return BriefResponse(date=day, forecast_rain_in=rain_in, high_tide_flag=high_tide, crews=crews,
                         capacity_per_crew=capacity_per_crew, items=items, fallback_mode=fallback_mode)


def age_factor(age_days: float) -> FactorContribution:
    """Case age factor: decays linearly from the full weight to 0 at the horizon."""
    w = weights()["backlog"]
    horizon = float(w["age_horizon_days"])
    value = max(0.0, 1.0 - age_days / horizon)
    return FactorContribution(factor="Recently reported", value=round(age_days, 1), contribution=w["age"] * value)


def build_backlog(as_of: datetime, limit: int, scores: dict[str, CellScore], cells: list[Cell],
                  reports: list[Report]) -> list[BacklogItem]:
    """Open cases ranked by cell priority without rain terms plus a case-age factor."""
    max_evidence = int(weights()["brief_defaults"]["max_evidence"])
    cell_map = {c.cell_id: c for c in cells}
    by_cell = _by_cell(reports)
    items: list[tuple[float, str, BacklogItem]] = []
    for r in reports:
        if r.status != ReportStatus.open:
            continue
        age = max(0.0, (as_of - r.opened_at).total_seconds() / 86400)
        cs = scores.get(r.cell_id)
        base = [f for f in (cs.factors if cs else ()) if not is_rain_factor(f)]
        factors = base + cell_factors(cell_map.get(r.cell_id), high_tide=False) + [age_factor(age)]
        others = evidence_for([x for x in by_cell.get(r.cell_id, []) if x.ticket_id != r.ticket_id],
                              _day(as_of), max_evidence - 1)
        score = total(factors)
        items.append((score, r.ticket_id, BacklogItem(
            ticket_id=r.ticket_id, cell_id=r.cell_id, opened_at=r.opened_at, age_days=round(age, 3),
            cause_label=r.cause_label, note_blank=r.note_blank,
            status_label=STATUS_UNCLEAR if r.note_blank else "Open",
            priority_score=score, factors=factors, evidence_ticket_ids=[r.ticket_id] + others)))
    items.sort(key=lambda t: (-t[0], t[1]))
    return [it for _, _, it in items[:limit]]
