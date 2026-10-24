"""DrainFast V1 API (FastAPI). Endpoints and shapes follow contracts/openapi.yaml.

Run: make api  (uvicorn backend.app:app --reload --port 8000)
"""
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Path as PathParam, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import model_adapter, priority, sources, store
from backend.config import fallback_on, frontend_origin, weights
from contracts.schemas import BacklogItem, BacktestResult, BriefResponse, RainTrendPoint, Report

log = logging.getLogger(__name__)
BOSTON = ZoneInfo("America/New_York")
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app = FastAPI(title="DrainFast API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[frontend_origin()], allow_methods=["GET"], allow_headers=["*"])


class HealthResponse(BaseModel):
    """Mirrors the HealthResponse component in contracts/openapi.yaml (not a contracts model)."""
    status: str
    fallback: bool


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """422 with {"detail": "<message>"} as a string, per ErrorResponse."""
    msgs = [f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg', 'invalid')}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(msgs) or "invalid request"})


def _today() -> date:
    """Today's date in Boston."""
    return datetime.now(BOSTON).date()


def _weather_for(day: date, rain_override: Optional[float] = None) -> tuple[float, bool, bool]:
    """(rain_in, high_tide, fallback_mode) for a brief date.

    Past dates use the recorded storm day (no record means 0 in and no high tide).
    Today and later use the live forecast; if it is unavailable, 1.0 in and fallback_mode.
    A rain_override (forecast_rain_in) replaces the rain for any date; tide is unchanged.
    """
    if day < _today():
        storms, _ = store.load_storms()
        rec = next((s for s in storms if s.storm_day == day), None)
        rain_in, tide_flag = (rec.rain_total_in, rec.high_tide_flag) if rec else (0.0, False)
        return (rain_in if rain_override is None else rain_override), tide_flag, False
    tide = sources.tide_outlook(day)
    if rain_override is not None:
        return rain_override, tide.high_tide_flag, False
    rain = sources.rain_forecast(day)
    if rain.fallback or rain.rain_in is None:
        return float(weights()["brief_defaults"]["fallback_rain_in"]), tide.high_tide_flag, True
    return rain.rain_in, tide.high_tide_flag, False


class ForecastDay(BaseModel):
    date: date
    rain_in: float


class OutlookResponse(BaseModel):
    """Next storm in the NWS forecast and whether the pre-storm brief should show.

    Backend-local (not yet in contracts/openapi.yaml): needs a "contract:" PR.
    """
    today: date
    threshold_in: float
    lookahead_days: int
    days: list[ForecastDay]
    next_storm: Optional[ForecastDay]
    brief_active: bool
    check_by: Optional[date]
    fallback: bool
    message: str


def _weekday(d: date) -> str:
    """'Thursday' for a date."""
    return d.strftime("%A")


@app.get("/outlook", response_model=OutlookResponse, operation_id="get_outlook")
def get_outlook() -> OutlookResponse:
    """Look ahead over the forecast: next storm, and whether to show the brief.

    The forecast decides when to show the list; the model (via /brief) decides which
    spots go first. Threshold and lookahead come from backend/weights.yaml.
    """
    cfg = weights()["storm"]
    today = _today()
    o = sources.storm_outlook(today, float(cfg["threshold_in"]), int(cfg["lookahead_days"]))
    storm = ForecastDay(**o.next_storm) if o.next_storm else None
    if o.fallback:
        message = "Forecast unavailable. Pick a date or enter expected rain to see the brief."
    elif storm is None:
        message = "No storm in the forecast. Routine cleaning continues."
    elif not o.brief_active:
        message = (f"Next storm: {_weekday(storm.date)}, about {storm.rain_in:.1f} in. "
                   f"The brief turns on {o.lookahead_days} days before.")
    else:
        when = "today" if storm.date == today else _weekday(storm.date)
        by = "now" if o.check_by == today.isoformat() else f"by {_weekday(date.fromisoformat(o.check_by))}"
        message = (f"Storm expected {when}, about {storm.rain_in:.1f} in. "
                   f"Check these locations first, {by}.")
    return OutlookResponse(today=today, threshold_in=o.threshold_in, lookahead_days=o.lookahead_days,
                           days=[ForecastDay(**d) for d in o.days], next_storm=storm,
                           brief_active=o.brief_active,
                           check_by=date.fromisoformat(o.check_by) if o.check_by else None,
                           fallback=o.fallback, message=message)


@app.get("/health", response_model=HealthResponse, operation_id="get_health")
def get_health() -> HealthResponse:
    """Liveness and whether fallback mode is on."""
    return HealthResponse(status="ok", fallback=fallback_on())


@app.get("/brief", response_model=BriefResponse, operation_id="get_brief")
def get_brief(
    date: Annotated[date, Query(description="Brief date (YYYY-MM-DD)")],
    crews: Annotated[int, Query(ge=1)],
    capacity_per_crew: Annotated[int, Query(ge=1)] = 30,
    forecast_rain_in: Annotated[Optional[float], Query(ge=0, le=30,
                                description="Optional rain override in inches (contract PR #3)")] = None,
) -> BriefResponse:
    """Ranked cells to clear first, filling crews x capacity_per_crew basins."""
    rain_in, high_tide, fallback_mode = _weather_for(date, forecast_rain_in)
    reports, _ = store.load_reports()
    cells, _ = store.load_cells()
    scores, _ = model_adapter.score(reports, date, rain_in, high_tide)
    return priority.build_brief(date, crews, capacity_per_crew, rain_in, high_tide, scores, cells, reports,
                                fallback_mode or fallback_on())


@app.get("/backlog", response_model=list[BacklogItem], operation_id="get_backlog")
def get_backlog(limit: Annotated[int, Query(ge=1)] = 50) -> list[BacklogItem]:
    """Open storm-related cases ranked by backlog priority."""
    now = datetime.now(BOSTON)
    reports, _ = store.load_reports()
    cells, _ = store.load_cells()
    scores, _ = model_adapter.score(reports, now.date(), 0.0, False)
    return priority.build_backlog(now, limit, scores, cells, reports)


@app.get("/cells/{cell_id}/history", response_model=list[Report], operation_id="get_cell_history",
         responses={404: {"description": "Unknown cell"}})
def get_cell_history(cell_id: Annotated[str, PathParam()]) -> list[Report]:
    """A cell's reports, newest first (same function as the MCP cell_history tool)."""
    hist = sources.cell_history(cell_id)
    if hist.total_reports == 0:
        cells, _ = store.load_cells()
        if not any(c.cell_id == cell_id for c in cells):
            raise HTTPException(status_code=404, detail=f"Unknown cell: {cell_id}")
    return hist.reports


@app.get("/backtest", response_model=list[BacktestResult], operation_id="get_backtest")
def get_backtest() -> list[BacktestResult]:
    """Backtest hit rates against random and most-past-complaints, with sample sizes."""
    return store.load_backtest()[0]


@app.get("/rain-trend", response_model=list[RainTrendPoint], operation_id="get_rain_trend")
def get_rain_trend() -> list[RainTrendPoint]:
    """Heavy-rain days (1 inch or more) per year at Boston Logan."""
    return store.load_rain_trend()[0]


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="web")
