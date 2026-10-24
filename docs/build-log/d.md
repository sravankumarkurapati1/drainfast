# Build log: D (frontend, local run scripts)

## Spec local-dev-macos (branch sravankumarkurapati)
- Requirements-first spec: `.kiro/specs/local-dev-macos/` (10 EARS requirements, design with 6 correctness properties, tasks with a wave dependency graph).
- Run with Kiro's task orchestrator: each task went to a `spec-task-execution` sub-agent, up to 5 in parallel per wave (test tooling, Vite helpers, fixtures, demo badge and `.env.example` ran together).
- Delivered: Vite app moved into `frontend/`, dev proxy for `/health /brief /backlog /cells /backtest /rain-trend` to `localhost:8000` (regex-matched, so `/healthcheck` is not proxied; strict port 5173; 502 JSON when the API is down), API client with `VITE_API_URL` or relative URLs, 10 s timeout and fixture fallback, "demo data" badge, `scripts/setup.sh`, `scripts/dev.sh`, `scripts/prod_local.sh` (bash 3.2, `lsof` port checks, process-group cleanup on Ctrl+C), README "Run locally".
- Dashboard: morning brief, priority map, backlog, backtest and heavy-rain trend. Plain-language factor and cause labels (product rule 5), ticket evidence on every row (rule 2), factor breakdown per score (rule 3).

## Kiro did well
- Grounded the spec in the repo before writing it: found `frontend/` empty with the Vite app at the repo root, no Pages base path logic to keep, and `*.local` already in the template `.gitignore`.
- Fixtures were generated from `contracts/schemas.py` and validated against the real Pydantic models (`extra="forbid"`, factor sums, rank order, `note_blank` rule), with cell IDs from `contracts/cells.py`.
- Proxy design used a regex key after checking Vite's docs: a plain string key would also forward `/cellsfoo`.

## I corrected
- The Vite template had overwritten the committed `.gitignore` (dropping `.venv/`, `.env`, `data/processed/`) and `README.md`. Restored both with `git restore` and added `frontend/.gitignore` for `.env.local`.
- The app files were untracked, so the planned `git mv` would fail. Used plain `mv`.
- Local npm 10.9.2 crashes installing vitest ("edgesOut"); installed with `npx npm@11.6.2`. `npm ci` from the lockfile works on 10.9.2.
- CARTO tiles now return the same "API key required" image for every tile (checked by downloading tiles: identical bytes at different coordinates). Switched to keyless Esri (dark gray, imagery) and OpenStreetMap tiles.
- Replaced a hand-written Leaflet type shim that broke `tsc -b` with `@types/leaflet` 1.9.22.

## Integration with A, B and C (main at f719311)
- Merged main (A data, B model and backtest, C backend and MCP, contract PRs #3 and #4) with no conflicts. Never edited another owner's files.
- Fixes found against the live API:
  - The API has no `GET /cells` list (only `/cells/{id}/history`), so neighborhood names come from each cell's history; offline they come from the bundled fixture.
  - `HealthResponse` has a `fallback` field; the fixture lookup now matches endpoints exactly so `/cells/{id}/history` never returns the `/cells` fixture.
  - Added a "Rain what-if" input that sends `forecast_rain_in` (contract PR #3).
- Verified end to end: backend pytest 60 passed; every endpoint returned 200 through the Vite proxy; the backend served `frontend/dist` on :8000; the UI rendered against the live API with "Live API" shown and no demo badge.

## Storm banner and forecast fixes
- Banner says in words whether a storm is expected, using the contract's `STORM_DAY_THRESHOLD_IN` (1.0 in): "Storm likely tomorrow: 1.40 in forecast" or "No storm expected tomorrow: 0.00 in forecast". Done in the frontend; no API change needed from C.
- Bug: in fallback mode the backend uses `brief_defaults.fallback_rain_in` (1.0 in), which sits exactly on the threshold, so the banner said "Storm likely today: 1.00 in forecast" for a number that is not a forecast. The banner and rain card now follow the rain's source: live forecast, planning default ("Live forecast unavailable"), what-if, or recorded rain for past dates.
- Bug: the brief defaulted to today; product.md says tomorrow's forecast. Default is now tomorrow.
- Bug: data loaded once, so the page kept showing fallback results after the API restarted without fallback. Datasets now reload on tab focus, reconnect and every 60 s.
- Live check (2026-10-24): brief for 2026-10-25 with fallback off returned 0.0 in, no high tide, `fallback_mode: false`, matching C's NWS check.

## Kiro features used by D
- Specs (requirements-first) and the task orchestrator with parallel sub-agents.
- Requirement-detailer sub-agents refined all 10 requirements in parallel.
- Steering (product, structure, tech) for scope, ownership and product rules.

## Open items
- Optional test tasks were skipped for time: the 6 fast-check properties, the bash script harness and the README check are specified in `tasks.md` but not written. Behaviour was checked with throwaway render and end-to-end runs instead.
- structure.md names `.kiro/specs/04-frontend/`; this work lives in `.kiro/specs/local-dev-macos/`.
- `scripts/` has no owner in structure.md; D wrote it for local runs.
- Requirement 10.3 (badge hides with a live API) is now verified; a real-browser check of the visuals is still to do.
