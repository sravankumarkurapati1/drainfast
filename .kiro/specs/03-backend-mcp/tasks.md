# Implementation Plan: 03-backend-mcp

## Overview

Build the DrainFast V1 backend (owner C): settings and weights, demo-file loaders with fixture fallback, the shared data sources, the model adapter, the pure priority builders, the FastAPI app and the MCP server, then offline pytest + Hypothesis tests in `tests/backend/`. The code is written and the 19 backend tests pass; the open items are the Kiro MCP demo, a Kiro CLI test run, and the switch to the merged contracts.

## Tasks

- [x] 1. Set up backend package, settings and test config
  - [x] 1.1 Create config.py, weights.yaml and test harness
    - `backend/config.py`: `fallback_on`, `demo_dir` (`DRAINFAST_DEMO_DIR` override), `fixtures_dir`, `user_agent` from `DRAINFAST_CONTACT`, `frontend_origin`, `weights()`
    - `backend/weights.yaml`: `brief`, `backlog`, `fallback_model` and `brief_defaults` (`fallback_rain_in: 1.0`, `max_evidence: 5`)
    - `tests/backend/conftest.py`: `DRAINFAST_FALLBACK=1`, autouse socket block, `empty_demo_dir` fixture
    - _Requirements: 1.2, 1.6, 3.5, 6.3_

- [x] 2. Implement backend/store.py
  - [x] 2.1 Loaders with fixture fallback and mtime cache
    - `_load` reads `.parquet` or `.json`, validates rows with contract models, skips invalid rows, falls back to `contracts/fixtures/`
    - `lru_cache` keyed by path and mtime; loaders for reports, cells, storms, backtest, rain trend
    - `tide_threshold_ft` accepts a number or a key containing "threshold"
    - _Requirements: 1.4, 5.5, 6.1_

- [x] 3. Implement backend/sources.py
  - [x] 3.1 Implement rain_forecast
    - NWS points -> `forecastGridData` -> `quantitativePrecipitation`; User-Agent on every request; 30-minute cache per date
    - `parse_duration` (`PnDTnHnM`); `rain_in_on_day` splits intervals across Boston midnight, DST-safe, mm to inches
    - _Requirements: 1.1, 1.2, 1.3, 1.6_
  - [x] 3.2 Implement tide_outlook and cell_history
    - CO-OPS 8443970 hilo predictions (MLLW, english, lst_ldt); flag when max exceeds `tide_threshold.json`
    - Pure `history_for`: newest first, total and `clogged_basin` counts; `as_json` for MCP
    - _Requirements: 1.4, 1.5, 1.6_
  - [x] 3.3 Write unit tests in test_sources.py
    - Duration parsing, midnight split, DST-day grid parse, network failure, no fetch in fallback, tide threshold
    - _Requirements: 1.1, 1.4, 1.6_

- [x] 4. Implement backend/model_adapter.py
  - [x] 4.1 Normalize score_cells output
    - DataFrame or list of dicts/objects; `contributions` mapping/list or `contrib_<feature>` / `<feature>_contribution` columns; plain factor names; `is_rain_factor` with a `\brain\b` regex
    - _Requirements: 3.1, 3.6_
  - [x] 4.2 History-only fallback scorer and score()
    - Uses only reports opened strictly before `as_of`; weights from `fallback_model`; used on ImportError, exception or empty output
    - _Requirements: 3.4, 3.5_

- [x] 5. Implement backend/priority.py
  - [x] 5.1 Factor helpers
    - `cell_factors` (EJ, flood area, high tide x flood area, BWSC share), `total`, `reason_for` (two largest positive factors), `evidence_for` (clogged first, before date, up to 5)
    - _Requirements: 3.1, 3.2, 4.5, 4.6_
  - [x] 5.2 build_brief
    - Skip cells without tickets; sort by score then `cell_id`; fill capacity by `basin_count` (0 counts as 1); ranks `1..n`
    - _Requirements: 4.4, 4.5, 4.6, 4.7_
  - [x] 5.3 build_backlog
    - Open cases; non-rain factors + location factors + linear age decay over 365 days; "Status unclear" when `note_blank`; evidence starts with the case; sort by score then `ticket_id`
    - _Requirements: 3.3, 5.1, 5.2, 5.3_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Write property-based tests in tests/backend/test_priority_properties.py
  - [x] 7.1 Create strategies.py
    - 8 fixed grid cells with random basins, owner and flags; 1 to 40 reports with random dates, status, cause and `note_blank`
    - _Requirements: 7.1-7.4_
  - [x] 7.2 Write property test for factor sum
    - **Property 1: Factor sum**
    - **Validates: Requirements 3.1, 3.2, 3.3, 7.1**
  - [x] 7.3 Write property tests for brief and backlog evidence
    - **Property 2: Evidence**
    - **Validates: Requirements 4.6, 4.7, 5.1, 5.3, 7.2**
  - [x] 7.4 Write property test for determinism under shuffle
    - **Property 3: Determinism under shuffle**
    - **Validates: Requirements 4.4, 7.3**
  - [x] 7.5 Write property test for future reports
    - **Property 4: Future reports do not change the brief**
    - **Validates: Requirements 3.4, 4.6, 7.4**
  - [x] 7.6 Write property test for capacity
    - **Property 5: Capacity**
    - **Validates: Requirements 4.4**

- [x] 8. Implement backend/app.py
  - [x] 8.1 App setup
    - CORS for `FRONTEND_ORIGIN`; 422 handler with string `detail`; `/health`; mount `frontend/dist` at `/` when present
    - _Requirements: 5.6, 5.7, 6.2, 6.3_
  - [x] 8.2 GET /brief
    - Past dates from `storms.parquet`; today/future from `rain_forecast` and `tide_outlook`; forecast unavailable -> 1.0 in and `fallback_mode`
    - _Requirements: 4.1, 4.2, 4.3_
  - [x] 8.3 GET /backlog, /cells/{cell_id}/history, /backtest, /rain-trend
    - Unknown cell -> 404 `{"detail": ...}`; backtest and rain trend from `data/demo/`
    - _Requirements: 5.1, 5.4, 5.5_
  - [x] 8.4 Write API tests in test_api.py
    - Health, brief fallback, backlog evidence and "Status unclear", 422 string, 404, backtest, rain trend, MCP parity
    - _Requirements: 2.1, 4.3, 5.2-5.7_

- [ ] 9. Implement the MCP server
  - [x] 9.1 Write mcp_server/server.py
    - Official MCP SDK over stdio; tools `rain_forecast`, `tide_outlook`, `cell_history` calling `backend.sources` only
    - _Requirements: 2.1, 2.2_
  - [x] 9.2 Register MCP server in .kiro/settings/mcp.json (verified over stdio: 3 tools, live and fallback)
  - [x] 9.3 Ask Kiro for tomorrow's forecast through drainfast-data (Kiro CLI transcript in docs/build-log/c.md (Kiro CLI transcripts); IDE screenshot still optional)
    - _Requirements: 2.1, 2.2_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - [x] 10.1 Run make test once through Kiro CLI (21 passed)
  - [x] 10.3 Optional forecast_rain_in on GET /brief (contract PR #3) and tide threshold fallback from data/raw/tide
    - _Requirements: 1.4, 4.8_
  - [ ] 10.2 Swap local contract stand-ins for the real contracts once merged and re-run tests
    - _Requirements: 6.1_

## Notes

- Property tests use `max_examples=100, deadline=None` and run offline with `DRAINFAST_FALLBACK=1`
- `GET /brief` has no `forecast_rain_in` override in the contract; adding one needs a `contract:` PR

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["3.1", "3.2", "4.2", "5.1"] },
    { "id": 3, "tasks": ["3.3", "5.2", "5.3", "7.1"] },
    { "id": 4, "tasks": ["7.2", "8.1", "9.1"] },
    { "id": 5, "tasks": ["7.3", "8.2"] },
    { "id": 6, "tasks": ["7.4", "8.3"] },
    { "id": 7, "tasks": ["7.5", "8.4"] },
    { "id": 8, "tasks": ["7.6", "9.2"] },
    { "id": 9, "tasks": ["10.1"] },
    { "id": 10, "tasks": ["10.2"] }
  ]
}
```
