# Requirements Document: 03-backend-mcp

## Introduction

The DrainFast V1 backend (owner C). A FastAPI app and an MCP server that share one
set of Python functions (tech.md rule 11). The backend reads pipeline outputs from
`data/demo/`, falls back to `contracts/fixtures/` when a file is missing, builds the
priority score, crew brief and backlog, and serves the frontend build. It matches
`contracts/openapi.yaml` exactly and uses `contracts.schemas` models as response models.

## Glossary

- **Backend**: `backend/` (FastAPI app `backend.app:app`).
- **Sources**: `backend/sources.py`, the functions shared by the API and MCP server.
- **MCP_Server**: `mcp_server/server.py`, run with `python -m mcp_server.server`.
- **Priority_Builder**: `backend/priority.py` with weights in `backend/weights.yaml`.
- **Fallback_Mode**: `DRAINFAST_FALLBACK=1`, or a failed network call.
- **Evidence**: past 311 ticket IDs a result is based on.
- **Capacity**: `crews * capacity_per_crew` catch basins.

## Requirements

### Requirement 1: Shared data sources

**User Story:** As a crew supervisor, I want tomorrow's rain and tide in the brief, so that the list reflects the coming storm.

1. WHEN `rain_forecast(day)` is called, THE Sources SHALL fetch `api.weather.gov/points/42.3601,-71.0589`, follow `forecastGridData`, read `quantitativePrecipitation` (millimetres over ISO 8601 durations), and return the inches that fall within that local Boston date.
2. THE Sources SHALL send a User-Agent built from the `DRAINFAST_CONTACT` environment variable on every NWS request.
3. THE Sources SHALL reuse a forecast result for the same date for 30 minutes.
4. WHEN `tide_outlook(day)` is called, THE Sources SHALL fetch NOAA CO-OPS predictions for station 8443970 (datum MLLW, units english, time_zone lst_ldt, interval hilo) and set `high_tide_flag` when the day's maximum exceeds the threshold in `data/demo/tide_threshold.json`, or, until that file exists, the 95th percentile of daily maximum levels in `data/raw/tide/`.
5. WHEN `cell_history(cell_id)` is called, THE Sources SHALL return that cell's reports newest first, with the count of all reports and of `clogged_basin` reports.
6. IF a network call fails or Fallback_Mode is on, THEN THE Sources SHALL return a result with `fallback=true` and SHALL NOT raise.

### Requirement 2: MCP server

1. THE MCP_Server SHALL expose the tools `rain_forecast`, `tide_outlook` and `cell_history`, each calling the matching Sources function and nothing else.
2. THE MCP_Server SHALL run over stdio with the official MCP Python SDK.

### Requirement 3: Priority score

1. THE Priority_Builder SHALL build a brief priority from the model's per-feature contributions (`model.service.score_cells`) plus an EJ factor, a flood-area factor, a high-tide-in-flood-area factor and a BWSC-share factor, each a FactorContribution.
2. THE Priority_Builder SHALL set `priority_score` to exactly the sum of its factor contributions.
3. THE Priority_Builder SHALL build a backlog priority from the cell priority without any rain term, plus an age factor that decays to zero over 365 days.
4. IF `model.service` is missing or raises, THEN THE Priority_Builder SHALL use a history-only fallback scorer that reads only reports opened strictly before `as_of`.
5. THE Priority_Builder SHALL read every weight from `backend/weights.yaml`.
6. THE Priority_Builder SHALL use plain-language factor names ("Past clogged-drain reports", not `past_fixable_count`).

### Requirement 4: Crew brief

1. WHEN `GET /brief` is called for a past date, THE Backend SHALL use that day's actual rain and tide from `data/demo/storms.parquet`.
2. WHEN `GET /brief` is called for today or a future date, THE Backend SHALL use `rain_forecast` and `tide_outlook`.
3. IF the forecast is unavailable, THEN THE Backend SHALL use 1.0 inch of rain and set `fallback_mode` true.
4. THE Backend SHALL rank cells by priority, ties broken by `cell_id`, and add cells until their total basin count reaches Capacity (a cell with no basins counts as 1).
5. THE Backend SHALL give each item a one-sentence plain-language reason built from its two largest factors.
6. THE Backend SHALL attach up to 5 evidence ticket IDs per item: the most recent `clogged_basin` tickets, otherwise the most recent reports, all opened before the brief date.
7. THE Backend SHALL exclude cells with no tickets, so that every item has at least one evidence ticket ID.
8. WHERE `forecast_rain_in` is given (0 to 30 inches), THE Backend SHALL use it instead of the forecast or recorded rain for that date (contract PR #3).

### Requirement 5: Backlog, history, backtest, rain trend, health

1. WHEN `GET /backlog?limit=N` is called, THE Backend SHALL return open cases ranked by backlog priority (ties by `ticket_id`) with `age_days` and factors.
2. WHEN a backlog case has `note_blank` true, THE Backend SHALL set `status_label` to "Status unclear".
3. THE Backend SHALL attach at least one evidence ticket ID to every backlog item, starting with the case itself.
4. WHEN `GET /cells/{cell_id}/history` names an unknown cell, THE Backend SHALL return 404 with `{"detail": "..."}`.
5. THE Backend SHALL serve `GET /backtest` and `GET /rain-trend` from `data/demo/backtest.json` and `data/demo/rain_trend.json`.
6. WHEN `GET /health` is called, THE Backend SHALL return `{status: "ok", fallback: <Fallback_Mode>}`.
7. IF a request has invalid parameters, THEN THE Backend SHALL return 422 with `{"detail": "<message>"}` as a string.

### Requirement 6: Always starts

1. IF a `data/demo/` file is missing or unreadable, THEN THE Backend SHALL load the matching file from `contracts/fixtures/` and still start.
2. WHERE `frontend/dist` exists, THE Backend SHALL serve it at `/`.
3. THE Backend SHALL allow CORS from `FRONTEND_ORIGIN` (default `http://localhost:5173`).

### Requirement 7: Property tests

1. FOR ALL generated reports and cells, every brief and backlog item SHALL have `priority_score` equal to the sum of its factors.
2. FOR ALL generated inputs, every brief and backlog item SHALL have at least one evidence ticket ID, and every brief evidence ID SHALL belong to the item's cell and be opened before the brief date.
3. FOR ALL generated inputs, identical inputs in any order SHALL give identical rankings.
4. FOR ALL generated inputs, adding reports opened on or after `as_of` SHALL NOT change the fallback brief.
