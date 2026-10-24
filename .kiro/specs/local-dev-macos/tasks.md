# Implementation Plan: local-dev-macos

## Overview

Implementation is in TypeScript (frontend, vitest + fast-check) and bash 3.2 (scripts). Step 0 moves the root Vite app into `frontend/` and needs user approval first. Every later task targets `frontend/`, `scripts/` or `README.md` only. The Makefile, requirements.txt, backend/ and all other modules stay unchanged.

## Tasks

- [x] 1. Step 0: Move the root Vite app into `frontend/` (REQUIRES USER APPROVAL)
  - [x] 1.1 Move app files with `git mv` (ask the user before running; skip this task if approval is withheld)
    - Do not run this until the user explicitly approves. It deletes root files outside the allowed paths.
    - `git mv package.json package-lock.json index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json eslint.config.js public src frontend/`
    - Remove untracked root `node_modules/` and `dist/` only after confirming with the user
    - No file contents change; verify `cd frontend && npm ci && npm run build` exits 0 and writes `frontend/dist/index.html` and `frontend/dist/assets/`
    - Keep it as its own isolated commit so it can be dropped
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Frontend test tooling and Vite config
  - [x] 2.1 Add test tooling to `frontend/package.json`
    - Add `vitest`, `fast-check`, `jsdom` (and `@testing-library/react` for the badge test) as devDependencies pinned to exact versions compatible with Vite 8
    - Add scripts `"test": "vitest --run"` and `"test:pbt": "vitest --run tests/properties"`
    - Create `frontend/vitest.config.ts` (jsdom environment, `tests/**/*.test.ts(x)`); keep `tests/` outside the `tsc -b` includes
    - _Requirements: 1.1, 1.3_

  - [x] 2.2 Create `frontend/vite.helpers.ts`
    - Export `API_PATHS`, `API_PATH_PATTERN` (`^/(health|brief|backlog|cells|backtest|rain-trend)(?:[/?]|$)`), `isApiPath`, `normalizeBasePath`
    - Add `vite.helpers.ts` to the `include` of `frontend/tsconfig.node.json`
    - _Requirements: 2.1, 2.3, 2.5, 2.6_

  - [ ]* 2.3 Write property test for proxy path matching
    - **Property 1: Proxy path matching follows the API_Paths rule**
    - **Validates: Requirements 2.1, 2.3**
    - `frontend/tests/properties/isApiPath.test.ts`, numRuns ≥ 100, bias generators to near-misses (`/healthcheck`, `/Cells`, `//cells`, `/backtests`)

  - [ ]* 2.4 Write property test for base path normalization
    - **Property 2: Base path normalization**
    - **Validates: Requirements 2.5, 2.6**
    - `frontend/tests/properties/normalizeBasePath.test.ts`, include the idempotence check

  - [x] 2.5 Rewrite `frontend/vite.config.ts`
    - `defineConfig(({ command, mode }) => …)`; `base` is `normalizeBasePath(VITE_BASE_PATH)` only for `build`, `/` for `serve`; read `VITE_BASE_PATH` via `loadEnv` merged under `process.env`; document it in a comment
    - `server.port: 5173`, `strictPort: true`
    - Proxy keyed by `API_PATH_PATTERN` → `http://localhost:8000`, `changeOrigin: false`, no rewrite, `timeout`/`proxyTimeout` 30 000 ms
    - `configure` adds an `error` handler that writes 502 `{"detail":"Upstream API unavailable at http://localhost:8000"}` when headers are not yet sent, and never throws
    - _Requirements: 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 2.6 Write unit tests for the Vite config
    - `frontend/tests/unit/viteConfig.test.ts`: `serve` gives `base: '/'` even with `VITE_BASE_PATH` set; `build` with `VITE_BASE_PATH=drainfast` gives `/drainfast/`; `port: 5173`, `strictPort: true`
    - _Requirements: 1.6, 2.5, 2.6, 2.7_

  - [ ]* 2.7 Write proxy integration tests
    - `frontend/tests/integration/proxy.test.ts`: start Vite with `createServer` on a free port with a stub HTTP upstream
    - Assert method, headers, body and query are preserved; `/healthcheck` not forwarded; unreachable upstream returns 502 while `/` still returns 200
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. API client and fixtures
  - [x] 3.1 Create bundled fixtures
    - `frontend/src/api/fixtures/{health,brief,backlog,cells,backtest,rain-trend}.json` shaped after `contracts/schemas.py` (snake_case, a few Boston cells with factor contributions and evidence ticket IDs)
    - `frontend/src/api/fixtures/index.ts` exporting `fixtureFor(path)`: strip query, match exact or `/`-prefixed sub-path against `API_PATHS`
    - _Requirements: 3.4, 3.6_

  - [x] 3.2 Implement `frontend/src/api/client.ts`
    - `DataSource`, `ApiResult<T>`, `ApiError` (`kind: 'rejected' | 'unreachable'`, `status?`)
    - Pure `resolveBase`, `joinUrl`, `decideOutcome`; `apiGet<T>(path, { timeoutMs = 10_000 })` using `AbortController`
    - `ok` → `source: 'api'`; `fallback` → fixture with `source: 'fixture'` or `ApiError('unreachable')`; `rejected` → `ApiError('rejected', status)` without reading fixtures
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 3.3 Write property test for absolute URL joining
    - **Property 3: Absolute URL joining has exactly one separator**
    - **Validates: Requirements 3.1, 3.3**

  - [ ]* 3.4 Write property test for blank base
    - **Property 4: Blank base yields a same-origin relative URL**
    - **Validates: Requirements 3.2**

  - [ ]* 3.5 Write property test for fallback decision
    - **Property 5: Fallback decision by outcome**
    - **Validates: Requirements 3.4, 3.5, 3.6**
    - Stub `globalThis.fetch` with `vi.fn`, use `vi.useFakeTimers` for timeouts, spy on `fixtureFor` to assert it is not called on 4xx

  - [ ]* 3.6 Write unit tests for fixture shapes
    - `frontend/tests/unit/fixtures.test.ts`: each fixture has the required top-level keys of its schema; `fixtureFor('/cells?bbox=1')` returns the cells fixture; unknown path returns `undefined`
    - _Requirements: 3.4, 3.6_

- [x] 4. Demo badge and app wiring
  - [x] 4.1 Implement the source registry and badge
    - `frontend/src/data/sources.ts` with pure `showDemoBadge(sources)`
    - `frontend/src/data/DataSourceContext.tsx`: `DataSourceProvider` holding `Record<datasetKey, DataSource>` and a `report(key, source)` function
    - `frontend/src/components/DemoBadge.tsx`: `<span role="status">demo data</span>` with a high-contrast style that does not rely on color alone; hidden while the registry is empty
    - _Requirements: 3.7, 3.8_

  - [ ]* 4.2 Write property test for the demo badge
    - **Property 6: Demo badge iff any fixture-sourced dataset**
    - **Validates: Requirements 3.7, 3.8**

  - [x] 4.3 Wire the client and badge into `frontend/src/App.tsx`
    - Replace the Vite template with a minimal view wrapped in `DataSourceProvider`; add data hooks that call `apiGet` for `/health` and `/brief` and `report` their source
    - Render `<DemoBadge/>`; show inline "API unreachable and no sample data" or "Request rejected (status)" messages for `ApiError` so the page is never blank
    - Confirm `npm --prefix frontend run build` exits 0
    - _Requirements: 3.4, 3.5, 3.6, 3.7, 3.8, 10.2, 10.3_

  - [ ]* 4.4 Write unit test for `DemoBadge`
    - `frontend/tests/unit/DemoBadge.test.tsx`: renders `role="status"` only when a dataset is fixture-sourced
    - _Requirements: 3.7, 3.8_

- [x] 5. Frontend env file
  - [x] 5.1 Create `frontend/.env.example`
    - Only `VITE_API_URL=` (empty), with the comments from the design (optional, relative URL when blank, absolute URL with scheme e.g. `http://localhost:8000`, build-time, overrides in `frontend/.env.local`)
    - Confirm `git check-ignore frontend/.env.local` reports ignored and `frontend/.env.example` is not ignored
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 5.2 Write unit test for `.env.example`
    - `frontend/tests/unit/envExample.test.ts`: only variable is an empty `VITE_API_URL`; required comment phrases present
    - _Requirements: 4.1, 4.3, 4.4, 4.5_

- [x] 6. Checkpoint - Ensure all tests pass
  - Run `npm --prefix frontend test` and `npm --prefix frontend run build`. Ensure all tests pass, ask the user if questions arise.

- [x] 7. Scripts
  - [x] 7.1 Create `scripts/lib.sh`
    - `set -Eeuo pipefail`, `REPO_ROOT`, `die`, `port_owner` (via `lsof -nP -iTCP:<port> -sTCP:LISTEN -Fpc`), `require_venv`; bash 3.2 only (no `wait -n`, `mapfile`, associative arrays)
    - _Requirements: 5.8, 6.3, 6.15, 7.4, 8.4, 8.5_

  - [x] 7.2 Create `scripts/setup.sh`
    - Shebang `#!/usr/bin/env bash`, source `lib.sh`, `cd "$REPO_ROOT"`
    - Collect missing `python3.11`/`node` and print every `brew install …` to stderr before touching anything; create or validate `.venv` (3.11 check, die on invalid without modifying it)
    - Check `requirements.txt` and `frontend/package.json`; `step "pip install"` and `step "npm install"`; print `Setup complete.`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 8.3_

  - [x] 7.3 Create `scripts/dev.sh`
    - Venv check and activate; report all busy ports 8000/5173 with command and PID; pipeline steps only when demo data is missing, skipping absent modules and stopping on failure
    - Check `frontend/package.json` before starting the API; `set -m`; `make api &` only if `backend/app.py` exists (else print fixture note); `npm --prefix frontend run dev &`
    - Print `http://localhost:5173`; supervise both jobs; on exit of either, report it and stop the other
    - Guarded `cleanup` trap: TERM each process group, KILL after 4 s, exit within 5 s
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 6.13, 6.14, 6.15, 8.3, 10.5_

  - [x] 7.4 Create `scripts/prod_local.sh`
    - Venv check, `frontend/` and `npm` checks, port 8000 check before build
    - `VITE_API_URL= npm --prefix frontend run build || die "frontend build failed"`; activate venv; pass `DRAINFAST_FALLBACK=1` only when it equals `1`; print `http://localhost:8000`; `exec make api`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 8.3_

  - [x] 7.5 Make the scripts executable
    - `chmod +x scripts/setup.sh scripts/dev.sh scripts/prod_local.sh`
    - `git update-index --chmod=+x` on the three scripts after `git add`; confirm `git ls-files -s scripts/*.sh` shows `100755`
    - _Requirements: 8.1, 8.2_

  - [ ]* 7.6 Create the bash test harness
    - `scripts/tests/run.sh` (runs `scripts/tests/test_*.sh` with `/bin/bash`) and `scripts/tests/stubs/{lsof,make,npm,python3.11,node}` that log argv and `VITE_API_URL`/`DRAINFAST_FALLBACK` to `$STUB_LOG`, with control vars for busy port, exit code and long-running mode
    - Temp repo skeleton helper using `mktemp -d`
    - _Requirements: 5.1, 6.1, 7.1_

  - [ ]* 7.7 Write tests for `setup.sh`
    - `scripts/tests/test_setup.sh`: missing tools (one and both), new venv, reuse venv, invalid venv untouched, pip/npm failure names step, missing files, foreign cwd creates no files, second run idempotent
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_

  - [ ]* 7.8 Write tests for `dev.sh`
    - `scripts/tests/test_dev.sh`: missing venv, busy ports, pipeline order/skip/failure, demo data present, no backend, no frontend, server exits on its own, Ctrl+C stops all stub PIDs within 5 s, fallback env passthrough, foreign cwd
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12, 6.13, 6.14, 6.15_

  - [ ]* 7.9 Write tests for `prod_local.sh`
    - `scripts/tests/test_prod_local.sh`: port check before build, `VITE_API_URL` empty in build env while set in parent shell, build failure stops API, fallback only when `1`, missing venv/frontend/npm
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [ ]* 7.10 Write common script tests
    - `scripts/tests/test_common.sh`: line 1 shebang exact, `set -Eeuo pipefail` effective (failing pipeline stage stops script non-zero), git index mode `100755`
    - _Requirements: 8.1, 8.3, 8.4, 8.5_

- [x] 8. README
  - [x] 8.1 Add the "Run locally" section to `README.md`
    - Exactly five subsections in order: Setup, Development, Production-like, Docker, Fallback mode, with the commands and URLs from Requirement 9 as code blocks
    - Docker subsection notes port 8080 and fallback on by default
    - Four-row troubleshooting table (symptom | fix)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [ ]* 8.2 Write README check
    - `scripts/tests/test_readme.sh`: heading, five subsection headings in order, required commands and URLs, four troubleshooting rows
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [x] 9. Final checkpoint - Local verification on macOS
  - Run `bash scripts/tests/run.sh` and `npm --prefix frontend test`
  - Run `./scripts/setup.sh`; if it exits non-zero, record verification as failed and do not run `dev.sh`
  - Start `./scripts/dev.sh` in a separate terminal (long-running); confirm `curl -sf http://localhost:5173` succeeds within 60 s and the page renders fixture data with the "demo data" badge (`backend/app.py` is not merged yet)
  - Press Ctrl+C and confirm with `lsof -nP -iTCP:5173 -iTCP:8000 -sTCP:LISTEN` that both ports are free within 10 s
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 10.1, 10.2, 10.4, 10.5_

## Notes

- Task 1.1 must not run without explicit user approval. If it is skipped, later tasks assume the user moved the files by hand.
- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Requirement 10.3 (badge hides with a live API) can only be checked once `backend/app.py` lands; it is covered by Property 6 and the wiring in 4.3 until then.
- Serving `frontend/dist` from `backend.app` belongs to the backend owner; `prod_local.sh` depends on it but does not implement it.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "3.1", "4.1", "5.1", "7.1"] },
    { "id": 2, "tasks": ["2.3", "2.4", "2.5", "3.2", "4.2", "5.2", "7.2", "7.3", "7.4", "8.1"] },
    { "id": 3, "tasks": ["2.6", "2.7", "3.3", "3.4", "3.5", "3.6", "4.3", "4.4", "7.5", "7.6"] },
    { "id": 4, "tasks": ["7.7", "7.8", "7.9", "7.10", "8.2"] }
  ]
}
```
