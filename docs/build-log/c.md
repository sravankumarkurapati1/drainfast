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

## Open items
- Swap the local contract stand-ins for the real contracts/schemas.py once merged, then re-run `make test`.
- Ask Kiro "Using drainfast-data, what's tomorrow's rain forecast and tide outlook?" and screenshot it.
- Run `make test` once through the Kiro CLI.
- Contract gap: `GET /brief` has no `forecast_rain_in` override parameter.
