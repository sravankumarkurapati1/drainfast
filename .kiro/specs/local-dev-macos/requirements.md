# Requirements Document

## Introduction

This feature makes DrainFast simple to run locally on macOS. It adds a Vite dev proxy, an API client that works with or without a configured API URL, setup and run scripts, and a "Run locally" section in the README.

Scope is limited to files in `frontend/`, `scripts/` and `README.md`. The Makefile, requirements.txt, backend/ and all other modules stay unchanged.

Project facts this spec is grounded in (checked at spec time):

- `frontend/` is currently empty. The Vite + React app (vite.config.ts, package.json, index.html, src/, tsconfig files) lives at the repo root. The Dockerfile and the Makefile `web` target both expect the app in `frontend/`.
- The root `vite.config.ts` has no GitHub Pages base path logic yet.
- The root `.gitignore` contains `*.local`, which already matches `frontend/.env.local`.
- `backend/`, `model/`, `contracts/fixtures/` and `contracts/openapi.yaml` do not exist yet. The Makefile defines `data`, `cells`, `model` and `api` targets that call `data_pipeline.run`, `data_pipeline.cells`, `model.run` and `backend.app:app`.
- The Dockerfile serves on port 8080 with `DRAINFAST_FALLBACK=1`.

Open decisions:

- (a) Moving the root Vite app into `frontend/` requires deleting root files (package.json, package-lock.json, index.html, vite.config.ts, tsconfig files, eslint.config.js, public/, src/) that sit outside the allowed paths. This needs user approval.
- (b) The Pages_Base_Path is new; no base path logic exists today. The Pages_Base_Path is to be set through an environment variable at build time.
- (c) The Dockerfile defaults to `DRAINFAST_FALLBACK=1` on port 8080 without `--reload`, while the Prod_Local_Script uses `make api` on port 8000 with Fallback_Mode opt-in only.

## Glossary

- **Frontend_App**: The React + Vite + TypeScript web app located in `frontend/`.
- **Vite_Config**: The file `frontend/vite.config.ts`.
- **Dev_Proxy**: The Vite dev server proxy defined in Vite_Config, active only while the Vite dev server runs.
- **API_Paths**: The URL path prefixes `/health`, `/brief`, `/backlog`, `/cells`, `/backtest` and `/rain-trend`.
- **Local_API**: The FastAPI server started by `make api`, listening on `http://localhost:8000`.
- **API_Client**: The module `frontend/src/api/client.ts`, through which all Frontend_App HTTP calls go.
- **VITE_API_URL**: An optional build-time environment variable holding the absolute base URL of the API.
- **Fixture_Data**: Static sample responses bundled with the Frontend_App, used when the API is unreachable.
- **Demo_Badge**: A visible "demo data" label shown in the Frontend_App while Fixture_Data is displayed.
- **Pages_Base_Path**: The base path Vite uses when building for GitHub Pages.
- **Setup_Script**: The executable `scripts/setup.sh`.
- **Dev_Script**: The executable `scripts/dev.sh`.
- **Prod_Local_Script**: The executable `scripts/prod_local.sh`.
- **Venv**: The Python virtual environment at `.venv/` in the repo root.
- **Demo_Data**: The committed pipeline outputs in `data/demo/`.
- **Pipeline_Step**: One of `make data`, `make cells`, `make model`, each tied to a Python module (`data_pipeline.run`, `data_pipeline.cells`, `model.run`).
- **Fallback_Mode**: Running with `DRAINFAST_FALLBACK=1`, which disables all Bedrock calls.
- **README**: The root `README.md`.

## Requirements

### Requirement 1: Frontend location

**User Story:** As a developer, I want the Vite app to live in `frontend/`, so that the scripts, the Makefile `web` target and the Dockerfile all find the app in the same place.

#### Acceptance Criteria

1. THE Frontend_App SHALL contain, directly inside `frontend/`, its own package.json, package-lock.json, index.html, Vite_Config, TypeScript config files (tsconfig.json, tsconfig.app.json, tsconfig.node.json), ESLint config, public/ folder and src/ folder, with every runtime and dev dependency currently declared in the repo-root package.json (including react, react-dom, leaflet and react-leaflet) declared in `frontend/package.json`.
2. WHEN `npm ci` is run inside `frontend/` on a clean checkout with no existing `frontend/node_modules/`, THE Frontend_App SHALL install all dependencies and exit with code 0, without reading any package.json, package-lock.json or node_modules/ outside `frontend/`.
3. WHEN `npm run build` is run inside `frontend/` after dependencies are installed, THE Frontend_App SHALL run the TypeScript type check followed by the Vite production build, exit with code 0, and write the build output to `frontend/dist/` containing an index.html file and an assets/ folder.
4. IF the TypeScript type check or the Vite build fails during `npm run build` inside `frontend/`, THEN THE Frontend_App SHALL exit with a non-zero code, print an error naming the failing file, and leave no newly written output outside `frontend/`.
5. WHEN `npm run dev` is run inside `frontend/`, or `make web` is run from the repo root, THE Frontend_App SHALL serve the app on port 5173 and respond to a request for `http://localhost:5173/` with the contents of `frontend/index.html` within 10 seconds of the command starting.
6. IF port 5173 is already in use when `npm run dev` is run inside `frontend/`, THEN THE Frontend_App SHALL exit with a non-zero code and print an error indicating that port 5173 is unavailable, instead of serving on a different port.

### Requirement 2: Vite dev proxy

**User Story:** As a developer, I want the dev server to forward API calls to the local API, so that the frontend talks to the backend with no CORS setup.

#### Acceptance Criteria

1. WHILE the Vite dev server is running, WHEN the dev server receives a request whose path equals one of the API_Paths or starts with one of the API_Paths followed by `/` or `?`, THE Dev_Proxy SHALL forward that request to Local_API with the path unchanged (for example, `/cells?bbox=1` goes to `http://localhost:8000/cells?bbox=1`, and `/healthcheck` is not forwarded).
2. WHILE the Vite dev server is running, WHEN the Dev_Proxy forwards a request to Local_API, THE Dev_Proxy SHALL keep the original HTTP method, query string, request body and request headers, and SHALL send Local_API's response status, headers and body back to the browser unchanged, so the browser treats the response as same-origin and needs no CORS headers.
3. WHILE the Vite dev server is running, THE Dev_Proxy SHALL serve every request whose path does not match one of the API_Paths under the rule in criterion 1 from the Vite dev server, and SHALL NOT forward it to Local_API.
4. WHILE the Vite dev server is running, IF Local_API cannot be reached when a request matching one of the API_Paths arrives (connection refused, or no response within 30 seconds), THEN THE Dev_Proxy SHALL send the browser an error response showing that the upstream API is unavailable, and the Vite dev server SHALL keep running and keep serving non-API paths.
5. WHERE a Pages_Base_Path is configured for a production build, THE Vite_Config SHALL use that Pages_Base_Path, with exactly one leading and one trailing `/` (for example, `/drainfast/`), as the prefix for every asset URL in the build output.
6. WHERE no Pages_Base_Path is configured for a production build, THE Vite_Config SHALL use `/` as the base path for the build output.
7. WHILE the Vite dev server is running, THE Vite_Config SHALL use `/` as the base path, whether or not a Pages_Base_Path is configured, so that requests to the API_Paths reach the Dev_Proxy without a prefix.

### Requirement 3: API client base URL

**User Story:** As a developer, I want the API client to pick its base URL from the environment, so that the same code works with the dev proxy, the single production container and a separately hosted API.

#### Acceptance Criteria

1. WHERE VITE_API_URL is set at build time to a value containing at least one non-whitespace character, THE API_Client SHALL send every request to a URL formed by the VITE_API_URL value followed by the request path, with the request path unchanged.
2. WHERE VITE_API_URL is unset, empty, or contains only whitespace at build time, THE API_Client SHALL send every request to a relative URL that starts with "/" so that the request resolves against the page's own origin.
3. WHERE VITE_API_URL ends with one or more trailing slashes, THE API_Client SHALL produce request URLs that contain exactly one slash between the base URL and the path, whether or not the request path starts with a slash.
4. IF a request from the API_Client fails with a network error, receives no response within 10 seconds, or receives an HTTP status from 500 to 599 inclusive, THEN THE API_Client SHALL return the Fixture_Data that matches the same request path to the caller, marked as fixture-sourced, instead of raising an error.
5. IF a request from the API_Client receives an HTTP status from 400 to 499 inclusive, THEN THE API_Client SHALL return an error to the caller indicating the request was rejected and SHALL NOT return Fixture_Data for that request.
6. IF a request from the API_Client fails under the conditions in criterion 4 and no Fixture_Data exists for that request path, THEN THE API_Client SHALL return an error to the caller indicating the API is unreachable and no sample data is available.
7. WHILE the Frontend_App displays at least one dataset sourced from Fixture_Data, THE Frontend_App SHALL show the Demo_Badge on screen.
8. WHILE every dataset the Frontend_App displays was returned by the API, THE Frontend_App SHALL hide the Demo_Badge.

### Requirement 4: Frontend environment file

**User Story:** As a developer, I want a documented example env file, so that I know VITE_API_URL exists and that it is optional.

#### Acceptance Criteria

1. THE Frontend_App SHALL include `frontend/.env.example` in which VITE_API_URL is the only variable defined, and the VITE_API_URL line is either commented out or set to an empty value, so that a copy of the file left unchanged leaves VITE_API_URL unset.
2. THE repository SHALL exclude `frontend/.env.local` from git tracking through the root `.gitignore` pattern `*.local` or through a `frontend/.gitignore` entry, so that `git check-ignore frontend/.env.local` reports the path as ignored.
3. THE `frontend/.env.example` file SHALL contain comments stating that VITE_API_URL is optional, and that WHERE VITE_API_URL is unset or empty the API_Client sends every request to a relative URL on the page's own origin.
4. THE `frontend/.env.example` file SHALL contain comments stating that a set VITE_API_URL value must be an absolute base URL including the scheme, giving `http://localhost:8000` (the Local_API address) as an example value.
5. THE `frontend/.env.example` file SHALL contain comments stating that VITE_API_URL is read at build time, so a changed value takes effect only after the Vite dev server is restarted or the Frontend_App is rebuilt, and that local overrides belong in `frontend/.env.local`.
6. THE repository SHALL track `frontend/.env.example` in git, so that `git check-ignore frontend/.env.example` reports the path as not ignored.

### Requirement 5: Setup script

**User Story:** As a developer on macOS, I want one setup command, so that I get a working Python and Node environment without reading install docs.

#### Acceptance Criteria

1. WHEN the Setup_Script runs, THE Setup_Script SHALL check that `python3.11` and `node` are available on PATH before it creates the Venv or installs any dependency.
2. IF `python3.11` is missing from PATH, THEN THE Setup_Script SHALL print `brew install python@3.11` to stderr, exit with a non-zero status, and leave the Venv and `frontend/node_modules` unchanged.
3. IF `node` is missing from PATH, THEN THE Setup_Script SHALL print `brew install node` to stderr, exit with a non-zero status, and leave the Venv and `frontend/node_modules` unchanged; if `python3.11` is also missing, THE Setup_Script SHALL print both install commands before exiting.
4. WHEN the tool checks pass and no `.venv/` directory exists at the repository root, THE Setup_Script SHALL create the Venv with `python3.11 -m venv .venv` at the repository root.
5. WHEN the tool checks pass and the Venv exists with an interpreter at `.venv/bin/python` that reports Python version 3.11, THE Setup_Script SHALL reuse the existing Venv without deleting or recreating it.
6. WHEN the Venv is ready, THE Setup_Script SHALL run `pip install -r requirements.txt` using the Venv's interpreter, then run `npm install` inside `frontend/`, then print a message indicating setup completed and exit with status 0.
7. WHEN the Setup_Script runs a second time on an already set-up machine, THE Setup_Script SHALL finish with exit status 0, keep the existing Venv without recreating it, and leave every package listed in `requirements.txt` importable from the Venv's interpreter and every dependency in `frontend/package.json` present in `frontend/node_modules`.
8. THE Setup_Script SHALL resolve the Venv, `requirements.txt`, and `frontend/` relative to the repository root (the parent directory of `scripts/`), so that starting it from any working directory creates or reuses the same `.venv/` at the repository root and creates no files in the working directory it was started from.
9. IF `pip install` or `npm install` exits with a non-zero status, or `requirements.txt` or `frontend/package.json` is missing, THEN THE Setup_Script SHALL print a message to stderr naming the failed step, skip all later steps, and exit with a non-zero status.
10. IF a `.venv/` directory exists but `.venv/bin/python` is missing or reports a Python version other than 3.11, THEN THE Setup_Script SHALL print a message to stderr indicating the Venv is invalid and must be removed, exit with a non-zero status, and leave the existing `.venv/` unmodified.

### Requirement 6: Development script

**User Story:** As a developer, I want one command that starts the API and the frontend together, so that I can open the app at http://localhost:5173 and stop everything with Ctrl+C.

#### Acceptance Criteria

1. WHEN the Dev_Script starts, THE Dev_Script SHALL activate the Venv at `.venv/` in the repository root before running any Pipeline_Step, Local_API, or the Frontend_App, so that `python` resolves to the Venv interpreter for every command the Dev_Script runs.
2. IF the Venv does not exist at `.venv/` in the repository root, THEN THE Dev_Script SHALL print a message telling the developer to run the Setup_Script, start no Pipeline_Step or server, and exit with a non-zero status.
3. IF port 8000 or port 5173 has a process listening on it when the Dev_Script starts, THEN THE Dev_Script SHALL print each busy port with the name and PID of the process listening on that port, start no Pipeline_Step or server, and exit with a non-zero status.
4. WHEN the Dev_Script starts and any of `cells.parquet`, `reports.parquet`, or `flood_area.geojson` is absent from Demo_Data, THE Dev_Script SHALL run the Pipeline_Steps one at a time in the order `make data`, `make cells`, `make model`, starting each step only after the previous step has exited.
5. WHEN the Dev_Script starts and `cells.parquet`, `reports.parquet`, and `flood_area.geojson` are all present in Demo_Data, THE Dev_Script SHALL skip all Pipeline_Steps and print a note that existing Demo_Data is being used.
6. IF the Python module behind a Pipeline_Step does not exist (`data_pipeline/run.py` for `make data`, `data_pipeline/cells.py` for `make cells`, `model/run.py` for `make model`), THEN THE Dev_Script SHALL skip that Pipeline_Step, print a note naming the skipped step, and continue with the next Pipeline_Step.
7. IF a Pipeline_Step exits with a non-zero status, THEN THE Dev_Script SHALL print the name of the failed step and its exit status, run no later Pipeline_Step, start no server, and exit with a non-zero status.
8. WHEN all Pipeline_Steps have finished or been skipped, THE Dev_Script SHALL start Local_API with `make api` in the background and then start the Frontend_App with `npm run dev` inside `frontend/`.
9. WHEN Local_API and the Frontend_App have been started, THE Dev_Script SHALL print the URL `http://localhost:5173` and keep running until the developer presses Ctrl+C.
10. IF the module `backend/app.py` does not exist, THEN THE Dev_Script SHALL print a note that the frontend will use Fixture_Data, skip `make api`, and start the Frontend_App without Local_API.
11. IF `frontend/package.json` does not exist, THEN THE Dev_Script SHALL print a message stating that the Frontend_App is not set up, stop any Local_API process it started, and exit with a non-zero status.
12. IF Local_API or the Frontend_App exits on its own while the Dev_Script is running, THEN THE Dev_Script SHALL print which of the two exited, stop the other one including its child processes, and exit with a non-zero status.
13. WHEN the developer presses Ctrl+C, THE Dev_Script SHALL stop Local_API and the Frontend_App, including their child processes, and exit within 5 seconds, after which no process started by the Dev_Script is listening on port 8000 or port 5173.
14. WHERE `DRAINFAST_FALLBACK=1` is set in the environment of the Dev_Script, THE Dev_Script SHALL pass `DRAINFAST_FALLBACK=1` to the environment of Local_API and of every Pipeline_Step it runs.
15. THE Dev_Script SHALL resolve the Venv, Demo_Data, `frontend/`, and the Makefile relative to the repository root, so that the checks, Pipeline_Steps, and servers it runs are the same no matter which working directory it is started from.

### Requirement 7: Production-like local script

**User Story:** As a developer, I want to run the app the way the deployed container runs it, so that I can check the production build before deploying.

#### Acceptance Criteria

1. WHEN the Prod_Local_Script runs, THE Prod_Local_Script SHALL check port 8000 before any build step, and only after confirming port 8000 is free SHALL run `npm run build` inside `frontend/` with VITE_API_URL unset in the build environment, even if VITE_API_URL is set in the developer's shell or in a `.env` file the script reads.
2. IF `npm run build` exits with a non-zero status, THEN THE Prod_Local_Script SHALL print a message stating the frontend build failed, exit with a non-zero status, and not start Local_API.
3. WHEN `npm run build` exits with status 0, THE Prod_Local_Script SHALL activate the Venv, print the URL http://localhost:8000, and run `make api`, so that Local_API serves the built Frontend_App from `frontend/dist` and the API at http://localhost:8000.
4. IF port 8000 is in use when the Prod_Local_Script starts, THEN THE Prod_Local_Script SHALL print the name and PID of the process using port 8000, exit with a non-zero status, and not run `npm run build` or start Local_API.
5. WHERE `DRAINFAST_FALLBACK=1` is set in the environment of the Prod_Local_Script, THE Prod_Local_Script SHALL pass `DRAINFAST_FALLBACK=1` to Local_API; IF `DRAINFAST_FALLBACK` is unset or set to any value other than `1`, THEN THE Prod_Local_Script SHALL start Local_API without setting `DRAINFAST_FALLBACK=1`.
6. IF the Venv directory `.venv/` does not exist or has no activate script, THEN THE Prod_Local_Script SHALL print a message naming the missing Venv and exit with a non-zero status before running `npm run build` or starting Local_API.
7. IF the `frontend/` directory does not exist or the `npm` command is not on the PATH, THEN THE Prod_Local_Script SHALL print a message naming the missing item and exit with a non-zero status without starting Local_API.
8. WHEN the developer stops Local_API with Ctrl+C, THE Prod_Local_Script SHALL exit within 5 seconds and leave no process listening on port 8000.

### Requirement 8: Script permissions

**User Story:** As a developer, I want the scripts to run directly, so that `./scripts/dev.sh` works without `bash` in front.

#### Acceptance Criteria

1. THE Setup_Script, Dev_Script and Prod_Local_Script SHALL each be recorded in the git index with file mode 100755, so that a fresh `git clone` on macOS produces files with the owner-executable bit set.
2. WHEN a developer runs `./scripts/setup.sh`, `./scripts/dev.sh` or `./scripts/prod_local.sh` from the repository root of a fresh clone on macOS, THE corresponding script SHALL start executing without a `bash` prefix and without a "permission denied" error.
3. THE Setup_Script, Dev_Script and Prod_Local_Script SHALL each have, as line 1 starting at the first character, a shebang that is exactly `#!/usr/bin/env bash` or `#!/bin/bash`.
4. IF any command in the Setup_Script, Dev_Script or Prod_Local_Script exits with a non-zero status, including a command that is not the last one in a pipeline, THEN THE script SHALL run no further commands after that failing command.
5. IF the Setup_Script, Dev_Script or Prod_Local_Script stops because of a failing command, THEN THE script SHALL exit with a non-zero exit status.

### Requirement 9: README "Run locally" section

**User Story:** As a new contributor or judge, I want short local run instructions, so that I can start DrainFast on a Mac in a few minutes.

#### Acceptance Criteria

1. THE README SHALL contain one section titled "Run locally" that contains exactly five subsections in this order: setup, development, production-like, Docker and Fallback_Mode.
2. THE README setup subsection SHALL list `python3.11` and `node` as prerequisites with the install commands `brew install python@3.11` and `brew install node`, and SHALL give `./scripts/setup.sh` as the setup command to run once from the repository root.
3. THE README development subsection SHALL give `./scripts/dev.sh` as the command and http://localhost:5173 as the URL to open, and SHALL state that the Setup_Script must have completed first.
4. THE README production-like subsection SHALL give `./scripts/prod_local.sh` as the command and http://localhost:8000 as the URL to open.
5. THE README Docker subsection SHALL give the commands `docker build -t drainfast .` and `docker run -p 8080:8080 drainfast` in that order, and http://localhost:8080 as the URL to open.
6. THE README Fallback_Mode subsection SHALL show `DRAINFAST_FALLBACK=1 ./scripts/dev.sh` as the command and SHALL state that Fallback_Mode disables all Bedrock calls.
7. THE README SHALL format every command in the "Run locally" section as a copy-pasteable code block or inline code span, with no placeholder values that the reader must edit.
8. THE README "Run locally" section SHALL contain a troubleshooting table with the columns symptom and fix, and exactly these four rows: Venv not active (fix: run `./scripts/setup.sh`, then `source .venv/bin/activate`), port 8000 or 5173 busy (fix: stop the process the Dev_Script names by PID, then rerun the command), Demo_Badge showing (fix: confirm the Local_API is running on port 8000, because the Demo_Badge means Fixture_Data is displayed), and `make` not found (fix: `xcode-select --install`).

### Requirement 10: Local verification

**User Story:** As a developer, I want the setup to be confirmed working, so that I know the scripts run on a real Mac.

#### Acceptance Criteria

1. WHEN the Setup_Script finishes with exit status 0 on macOS and the Dev_Script is then started from the repo root, THE Frontend_App SHALL respond with HTTP 200 to a GET request at http://localhost:5173 within 60 seconds of the Dev_Script starting.
2. WHILE the Dev_Script is running and Local_API is unavailable (not started, or `backend/app.py` does not exist), THE Frontend_App at http://localhost:5173 SHALL render Fixture_Data and show the Demo_Badge within 10 seconds of the page loading, with no blank screen and no unhandled error shown in the page.
3. WHILE the Dev_Script is running and Local_API answers requests on port 8000, THE Frontend_App at http://localhost:5173 SHALL render data returned by Local_API and hide the Demo_Badge.
4. IF the Setup_Script exits with a non-zero status, THEN the local verification SHALL be recorded as failed, and the Dev_Script SHALL NOT be run as part of that verification.
5. WHEN the Dev_Script used for verification is stopped with Ctrl+C, THE Dev_Script SHALL release ports 5173 and 8000 within 10 seconds, so that a repeat verification run does not fail with a busy-port error.
