---
inclusion: always
---
# DrainFast — Project Structure and Ownership

## Folder layout
```
drainfast/
├── .kiro/                 steering, specs, hooks, MCP settings (never gitignored)
├── contracts/             shared schemas, paths, OpenAPI spec, fixtures (frozen)
├── data_pipeline/         ingest 311, label causes, cells, duplicate pairs
├── model/                 storm days, features, training, ranking
├── evaluation/            backtest, baselines, equity metrics, dedupe evaluation
├── backend/               FastAPI app, triage, work orders, co-pilot, fallback
├── mcp_server/            MCP tools for 311, NWS forecast and tides
├── frontend/              React + Vite web app
├── tests/
│   ├── contracts/  data_pipeline/  model/  backend/
├── data/
│   ├── raw/               committed source downloads (311, rain, tide, basins, EJ, flood)
│   ├── processed/         gitignored scratch space
│   └── demo/              committed pipeline outputs; the app runs from here
├── docs/
│   ├── build-log/         a.md, b.md, c.md, d.md (one per person)
│   └── kiro-writeup.md
├── Makefile  requirements.txt  Dockerfile  README.md  .env.example
```

## Ownership
Each folder has exactly one owner. Only change files inside the module the current
task belongs to.

| Owner | Folders |
|---|---|
| A (data) | data_pipeline/, tests/data_pipeline/, .kiro/specs/01-ingest-and-labels/ |
| B (model) | model/, evaluation/, tests/model/, .kiro/specs/02-risk-model-backtest/ |
| C (backend, lead) | backend/, mcp_server/, tests/backend/, .kiro/specs/03-api-copilot/, .kiro/settings/mcp.json, Dockerfile, Makefile |
| D (frontend) | frontend/, .kiro/specs/04-frontend/, README.md, docs/kiro-writeup.md |
| Everyone (frozen) | contracts/, tests/contracts/, the three shared steering files |

## Module boundaries
Dependencies point one way only:
contracts ← data_pipeline ← model and evaluation ← backend ← frontend (over HTTP)

- All pipeline outputs go to data/demo/ (committed). data/raw/ is committed.
- Grid cells come from contracts/cells.py (cell_id, cell_center). Never redefine
  the grid.
- data_pipeline never imports from model, evaluation or backend. It exposes
  label_report(text) in data_pipeline/labeler.py for the backend to reuse.
- model exposes score_cells(as_of, rain_in, high_tide) in model/service.py. The
  backend builds the priority score, brief and backlog in backend/priority.py.
- evaluation exposes backtest and equity_view in evaluation/service.py.
- backend imports those public functions only, never private helpers.
  Nothing imports from backend.
- frontend talks to the backend only through HTTP, via frontend/src/api/client.ts.

## Naming
- Python files and functions: snake_case. Classes: PascalCase.
- Tests: tests/<module>/test_<thing>.py.
- React components: PascalCase.tsx in frontend/src/components/.
- Hooks: .kiro/hooks/<owner letter>-<name>.json (for example b-backtest.json).
- Module steering: .kiro/steering/<module>-rules.md with a fileMatch pattern.
- Extra specs for a module start with that module's number (01*, 02*, 03*, 04*).

## Dependencies
- Python packages are listed only in the root requirements.txt, pinned with ==.
  Ask C (owner) to add a package; do not create module requirements files.
- frontend/package.json belongs to the frontend owner.

## Git workflow
- main is protected. Changes arrive by pull request with one approval and passing tests.
- Branch names: <owner letter>/<phase>-<topic>, for example a/p1-ingest-labels.
- Rebase on origin/main before opening a pull request.
- Merge order at each phase gate: A, then B, then C, then D.
- Contract changes use a pull request titled "contract: ..." and need approval from
  every module that uses the changed contract.
- Never add .kiro/ to .gitignore. Never commit data/processed or .env.

## When a task needs something outside its module
Stop and say what is needed and which owner should change it. Do not edit another
module's files, and do not copy or redefine shared models locally.