# Build log: C (backend, MCP, setup)

## Step 0 setup (PR #1, branch chore/setup)
- Committed data/raw (311, Logan rain, tide 8443970, catch basins, EJ, 9 in flood extent), contracts/cells.py, Makefile, pinned requirements.txt, Dockerfile, .gitignore (.kiro never ignored), .env.example, steering updates.
- Kiro did well: applied the steering edits in place without touching the frontmatter (`inclusion: always` stays on line 1).
- Corrected: mcp 1.2+ needs pydantic>=2.10, which conflicts with the contract pin (2.9.2). Pinned mcp 1.1.3 and used the low-level Server API.

## Spec 03-backend-mcp (branch c/03-backend)
- Requirements-first spec: `.kiro/specs/03-backend-mcp/` (EARS requirements, design, tasks).
- Sub-agents: I split the work in parallel. One wrote design.md and tasks.md from the code, one verified the MCP server end to end over stdio and wrote `.kiro/settings/mcp.json`, and the custom-agent-creator wrote two custom agents. I wrote the hooks.
- Property tests (Hypothesis, 100 examples each): factor sum, evidence, determinism under shuffle, no future data, crew capacity. 19 backend tests pass offline.
- Bugs caught by tests:
  - The factor filter that drops rain terms from the backlog matched "drain" inside "Past clogged-drain reports". Fixed with a word-boundary regex (`\brain\b`).
  - The DST-day forecast test showed one hour of a 12-hour NWS block falls on the previous day because DST ended on Nov 1. The code was right; the test expectation was wrong.
- Live check (2026-10-24): NWS forecast 0.0 in for 2026-10-25 (dry week), NOAA high tide 10.79 ft MLLW at 10:56.

## Kiro features used by C
- Hooks: `c-citation-check` (PostFileSave on backend/*.py runs the evidence tests), `c-module-guard` (PreToolUse on writes, stops edits to frozen contracts or another owner's module), `c-backend-tests-on-stop` (Stop runs backend tests when backend files changed).
- MCP: `drainfast-data` server (rain_forecast, tide_outlook, cell_history), the same functions the API uses.
- Custom agents: `.kiro/agents/drainfast-pr-reviewer.md` (run before each merge), `.kiro/agents/drainfast-contract-checker.md` (API vs openapi.yaml, demo files vs schemas).

## Follow-ups done
- Kiro CLI (second tool): `make test` (21 passed) and the drainfast-data MCP forecast question, both run through `kiro-cli`. Transcripts are in `docs/build-log/c.md (Kiro CLI transcripts)`.
- Contract PR #3: optional `forecast_rain_in` on `GET /brief`. The backend already supports it.
- High-tide flag: until B's `tide_threshold.json` exists, the backend uses the 95th percentile of daily highs from `data/raw/tide` (12.177 ft MLLW).
- Security decision: the API has no authentication on purpose. It is read-only, serves only public 311, NOAA and NWS data, and the rules require judges to use the live link free and without restriction. CORS allows GET only from FRONTEND_ORIGIN. No secrets are exposed: Bedrock is off in the deployed container (DRAINFAST_FALLBACK=1).

## Integration with A and B (main at fd1ef48)
- Merged main twice and never edited A's or B's files.
- The backend now ranks with B's `model.service.score_cells`. The model is local, so it is used in fallback mode too. Results are cached per (date, rain, tide); the first call takes about 3 to 7 s, repeats about 0.07 s.
- Fixes for real pipeline files:
  - Non-contract columns (A's `exclude`, `bwsc_share`) are dropped before validation, and reports marked `exclude` are skipped.
  - B's `rain_trend.json` wraps its points in an object, so the loader reads `points`.
- Live numbers: 6,971 reports, 8,818 cells, 5,412 storm days, 3 backtest storms, 15 rain-trend years, and B's tide threshold of 12.177 ft. The brief for 2023-12-18 returns 9 cells with ticket evidence. 58 tests pass (A, B and C).

## Open items
- Swap the local contract stand-ins for the real contracts/schemas.py once merged, then re-run `make test`.
- Optional: an IDE screenshot of the same MCP question for the write-up.

## Kiro CLI transcripts

Run from the repo root with `kiro-cli 2.34.0` in non-interactive mode. The CLI loaded
`.kiro/settings/mcp.json` automatically, so the same `drainfast-data` MCP server the IDE
uses was available in the terminal.

## 1. make test

```
$ kiro-cli chat --no-interactive --trust-all-tools "In this repo, run exactly: make test PY=.venv/bin/python . Do not modify, create or delete any files. Report the pass/fail counts in one line."
[tool] Running: make test PY=.venv/bin/python
[tool] status: Completed
21 passed, 0 failed (1 warning).
```

## 2. MCP question: tomorrow's rain and tide

```
$ kiro-cli chat --no-interactive --trust-all-tools "Using the drainfast-data MCP server tools only (rain_forecast and tide_outlook), what is tomorrow's (2026-10-25) rain forecast and tide outlook for Boston? ..."
[tool] Running: @drainfast-data/rain_forecast
[tool] Running: @drainfast-data/tide_outlook
Rain forecast (rain_forecast)
- rain_in: 0.0
- fallback: false
- source: api.weather.gov
Tide outlook (tide_outlook)
- max_ft_mllw: 10.786
- threshold_ft_mllw: 12.177
- high_tide_flag: false
- highs: 2026-10-25 10:56 10.786 ft MLLW; 2026-10-25 23:25 10.152 ft MLLW
- source: NOAA CO-OPS 8443970
In short: no rain forecast (0.0 in) and no high-tide flag, with the day's peak tide
of 10.786 ft MLLW staying below the 12.177 ft threshold.
```

## How the CLI differed from the IDE
- No approval prompts with `--trust-all-tools`, and no chat panel. The prompt has to carry
  every constraint ("do not modify files"), because there is no supervised mode to catch
  a bad edit.
- It read the same `.kiro/` folder (MCP config) as the IDE, so no setup was needed.
- Good for scripted checks before a merge. The IDE is better for specs and reviewing diffs.
