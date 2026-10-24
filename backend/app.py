"""DrainFast V1 API (FastAPI). Endpoints and shapes follow contracts/openapi.yaml.

Run: make api  (uvicorn backend.app:app --reload --port 8000)
"""
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Annotated
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
    return datetime.now(BOSTON).date()


def _weather_for(day: date) -> tuple[float, bool, bool]:
    """(rain_in, high_tide, fallback_mode) for a brief date.

    Past dates use the recorded storm day (no record means 0 in and no high tide).
    Today and later use the live forecast; if it is unavailable, 1.0 in and fallback_mode.
    """
    if day < _today():
        storms, _ = store.load_storms()
        rec = next((s for s in storms if s.storm_day == day), None)
        return (rec.rain_total_in, rec.high_tide_flag, False) if rec else (0.0, False, False)
    rain = sources.rain_forecast(day)
    tide = sources.tide_outlook(day)
    if rain.fallback or rain.rain_in is None:
        return float(weights()["brief_defaults"]["fallback_rain_in"]), tide.high_tide_flag, True
    return rain.rain_in, tide.high_tide_flag, False


@app.get("/health", response_model=HealthResponse, operation_id="get_health")
def get_health() -> HealthResponse:
    """Liveness and whether fallback mode is on."""
    return HealthResponse(status="ok", fallback=fallback_on())


@app.get("/brief", response_model=BriefResponse, operation_id="get_brief")
def get_brief(
    date: Annotated[date, Query(description="Brief date (YYYY-MM-DD)")],
    crews: Annotated[int, Query(ge=1)],
    capacity_per_crew: Annotated[int, Query(ge=1)] = 30,
) -> BriefResponse:
    """Ranked cells to clear first, filling crews x capacity_per_crew basins."""
    rain_in, high_tide, fallback_mode = _weather_for(date)
    reports, _ = store.load_reports()
    cells, _ = store.load_cells()
    scores, _ = model_adapter.score(reports, date, rain_in, high_tide, use_model=not fallback_on())
    return priority.build_brief(date, crews, capacity_per_crew, rain_in, high_tide, scores, cells, reports,
                                fallback_mode or fallback_on())


@app.get("/backlog", response_model=list[BacklogItem], operation_id="get_backlog")
def get_backlog(limit: Annotated[int, Query(ge=1)] = 50) -> list[BacklogItem]:
    """Open storm-related cases ranked by backlog priority."""
    now = datetime.now(BOSTON)
    reports, _ = store.load_reports()
    cells, _ = store.load_cells()
    scores, _ = model_adapter.score(reports, now.date(), 0.0, False, use_model=not fallback_on())
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
