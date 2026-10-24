"""Functions shared by the API and the MCP server (tech.md rule 11).

rain_forecast and tide_outlook call public APIs. Any network failure, or
DRAINFAST_FALLBACK=1, returns a result with fallback=True; nothing here raises.
"""
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

import httpx

from backend.config import fallback_on, user_agent
from backend.store import load_reports, tide_threshold_ft
from contracts.schemas import CauseLabel, Report

log = logging.getLogger(__name__)
BOSTON = ZoneInfo("America/New_York")
NWS_POINT = "https://api.weather.gov/points/42.3601,-71.0589"
COOPS = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
TIDE_STATION = "8443970"
CACHE_SECONDS = 30 * 60
MM_PER_INCH = 25.4
# Failures that mean "no forecast right now": network, HTTP status, or an unexpected payload.
NETWORK_ERRORS = (httpx.HTTPError, OSError, KeyError, IndexError, TypeError, ValueError)

FetchJson = Callable[[str, Optional[dict[str, str]]], Any]


@dataclass
class RainForecast:
    date: str
    rain_in: Optional[float]
    fallback: bool
    source: str = "api.weather.gov"
    note: str = ""


@dataclass
class TideOutlook:
    date: str
    max_ft_mllw: Optional[float]
    threshold_ft_mllw: Optional[float]
    high_tide_flag: bool
    fallback: bool
    highs: list[dict[str, Any]] = field(default_factory=list)
    source: str = "NOAA CO-OPS 8443970"
    note: str = ""


@dataclass
class CellHistory:
    cell_id: str
    total_reports: int
    clogged_basin_reports: int
    reports: list[Report]

    def to_json(self) -> dict[str, Any]:
        """JSON-safe dict for the MCP server."""
        return {
            "cell_id": self.cell_id,
            "total_reports": self.total_reports,
            "clogged_basin_reports": self.clogged_basin_reports,
            "reports": [r.model_dump(mode="json") for r in self.reports],
        }


def _http_json(url: str, params: Optional[dict[str, str]] = None) -> Any:
    """GET a JSON document with the DrainFast User-Agent (NWS requires one)."""
    headers = {"User-Agent": user_agent(), "Accept": "application/geo+json, application/json"}
    with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$")


def parse_duration(text: str) -> timedelta:
    """Parse an ISO 8601 duration such as PT6H, P1D or P1DT12H."""
    m = _DURATION.match(text)
    if not m or not any(m.groups()):
        raise ValueError(f"unsupported ISO 8601 duration: {text!r}")
    d, h, mi = (int(g) if g else 0 for g in m.groups())
    return timedelta(days=d, hours=h, minutes=mi)


def rain_in_on_day(values: list[dict[str, Any]], day: date) -> float:
    """Inches of rain within the local Boston date `day`.

    `values` are NWS quantitativePrecipitation items: {"validTime": "<start>/<duration>",
    "value": <mm over the interval>}. Intervals crossing midnight are split in
    proportion to the hours that fall inside `day`.
    """
    start_day = datetime(day.year, day.month, day.day, tzinfo=BOSTON)
    end_day = start_day + timedelta(days=1)
    total_mm = 0.0
    for v in values:
        if v.get("value") is None:
            continue
        start_text, dur_text = v["validTime"].split("/")
        start = datetime.fromisoformat(start_text)
        end = start + parse_duration(dur_text)
        overlap = (min(end, end_day) - max(start, start_day)).total_seconds()
        if overlap > 0:
            total_mm += float(v["value"]) * overlap / (end - start).total_seconds()
    return round(total_mm / MM_PER_INCH, 3)


_rain_cache: dict[str, tuple[float, RainForecast]] = {}
_grid_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _grid_values(fetch: FetchJson) -> list[dict[str, Any]]:
    """NWS quantitativePrecipitation values for Boston (about 7 days), cached 30 minutes.

    Raises one of NETWORK_ERRORS on failure; callers turn that into fallback=True.
    """
    hit = _grid_cache.get("boston")
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    grid_url = fetch(NWS_POINT, None)["properties"]["forecastGridData"]
    values = fetch(grid_url, None)["properties"]["quantitativePrecipitation"]["values"]
    _grid_cache["boston"] = (time.monotonic(), values)
    return values


def rain_forecast(day: date, fetch: FetchJson = _http_json) -> RainForecast:
    """Forecast rain in inches for a local Boston date from the NWS grid forecast.

    Cached for 30 minutes per date. Returns fallback=True (rain_in None) on any failure.
    """
    key = day.isoformat()
    if fallback_on():
        return RainForecast(key, None, True, note="DRAINFAST_FALLBACK=1")
    hit = _rain_cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    try:
        result = RainForecast(key, rain_in_on_day(_grid_values(fetch), day), False)
    except NETWORK_ERRORS as e:
        log.warning("rain_forecast failed for %s: %s", key, e)
        return RainForecast(key, None, True, note=f"forecast unavailable: {type(e).__name__}")
    _rain_cache[key] = (time.monotonic(), result)
    return result


@dataclass
class StormOutlook:
    """Next storm in the forecast and whether the pre-storm brief should be on."""
    today: str
    threshold_in: float
    lookahead_days: int
    days: list[dict[str, Any]]          # [{"date": "YYYY-MM-DD", "rain_in": float}], today onward
    next_storm: Optional[dict[str, Any]]  # first day with rain_in >= threshold, or None
    brief_active: bool                  # next storm falls within lookahead_days of today
    check_by: Optional[str]             # the day before the storm (or today if the storm is today)
    fallback: bool
    source: str = "api.weather.gov"
    note: str = ""


def storm_outlook(today: date, threshold_in: float, lookahead_days: int,
                  fetch: FetchJson = _http_json) -> StormOutlook:
    """Daily forecast rain for the NWS forecast window (about 7 days) and the next storm.

    A storm day has rain_in >= threshold_in. The brief turns on only when the next
    storm is within lookahead_days of today (today counts as day 0). On any failure,
    or in fallback mode, returns fallback=True with no storm and brief_active False.
    """
    def empty(note: str) -> StormOutlook:
        return StormOutlook(today.isoformat(), threshold_in, lookahead_days, [], None, False, None, True, note=note)

    if fallback_on():
        return empty("DRAINFAST_FALLBACK=1")
    try:
        values = _grid_values(fetch)
        last = max(datetime.fromisoformat(v["validTime"].split("/")[0]).astimezone(BOSTON).date()
                   for v in values)
    except NETWORK_ERRORS as e:
        log.warning("storm_outlook failed: %s", e)
        return empty(f"forecast unavailable: {type(e).__name__}")
    days = [{"date": (today + timedelta(d)).isoformat(),
             "rain_in": rain_in_on_day(values, today + timedelta(d))}
            for d in range((last - today).days + 1)]
    storm = next((d for d in days if d["rain_in"] >= threshold_in), None)
    active = storm is not None and (date.fromisoformat(storm["date"]) - today).days <= lookahead_days
    check_by = None
    if storm is not None:
        check_by = max(today, date.fromisoformat(storm["date"]) - timedelta(days=1)).isoformat()
    return StormOutlook(today.isoformat(), threshold_in, lookahead_days, days, storm, active, check_by, False)


def tide_outlook(day: date, fetch: FetchJson = _http_json) -> TideOutlook:
    """Predicted high and low tides for a date at Boston (8443970, MLLW, feet).

    high_tide_flag is True when the day's highest prediction exceeds the threshold in
    data/demo/tide_threshold.json. Returns fallback=True on any failure.
    """
    key = day.isoformat()
    threshold = tide_threshold_ft()
    if fallback_on():
        return TideOutlook(key, None, threshold, False, True, note="DRAINFAST_FALLBACK=1")
    params = {
        "product": "predictions", "station": TIDE_STATION, "datum": "MLLW", "units": "english",
        "time_zone": "lst_ldt", "interval": "hilo", "format": "json", "application": "DrainFast",
        "begin_date": day.strftime("%Y%m%d"), "end_date": day.strftime("%Y%m%d"),
    }
    try:
        preds = fetch(COOPS, params)["predictions"]
        highs = [{"time": p["t"], "ft_mllw": float(p["v"])} for p in preds if p.get("type") == "H"]
        max_ft = max(float(p["v"]) for p in preds)
    except NETWORK_ERRORS as e:
        log.warning("tide_outlook failed for %s: %s", key, e)
        return TideOutlook(key, None, threshold, False, True, note=f"tide unavailable: {type(e).__name__}")
    flag = threshold is not None and max_ft > threshold
    note = "" if threshold is not None else "no tide threshold file; flag is False"
    return TideOutlook(key, max_ft, threshold, flag, False, highs=highs, note=note)


def history_for(cell_id: str, reports: list[Report]) -> CellHistory:
    """Pure helper: a cell's reports newest first, with counts."""
    mine = sorted((r for r in reports if r.cell_id == cell_id),
                  key=lambda r: (r.opened_at, r.ticket_id), reverse=True)
    clogged = sum(r.cause_label == CauseLabel.clogged_basin for r in mine)
    return CellHistory(cell_id, len(mine), clogged, mine)


def cell_history(cell_id: str) -> CellHistory:
    """A cell's 311 reports newest first, with counts of all and clogged-drain reports."""
    reports, _ = load_reports()
    return history_for(cell_id, reports)


def as_json(obj: Any) -> dict[str, Any]:
    """JSON-safe dict of a RainForecast, TideOutlook or CellHistory."""
    return obj.to_json() if isinstance(obj, CellHistory) else asdict(obj)
