# How we used Kiro to build DrainFast

**Track:** Climate Tech (Hackachusetts C1, resilient communities)
**Team:** A data and labels · B model and backtest · C backend, MCP and setup (lead) · D frontend and local run scripts

## What DrainFast is

Boston has more than 30,000 catch basins, and BWSC crews clean about 60 a day. DrainFast
tells crew supervisors which places to clear first before a storm. It ranks ~100 m grid
cells by how likely they are to have flooding that clearing a catch basin would fix, using
Boston 311 tickets, Logan Airport rainfall, the National Weather Service forecast, NOAA
tides, BWSC catch basin locations, environmental justice block groups and the Climate Ready
Boston flood map.

The app is one dashboard:
- **Storm banner:** says in words whether a storm is expected, for example "Storm likely
  tomorrow: 1.40 in forecast" or "No storm expected tomorrow: 0.00 in forecast", and where
  the rain number came from (live forecast, planning default, what-if, or recorded rain).
- **Morning brief and priority map:** for a date (tomorrow by default, or a past storm), a
  number of crews and an optional "rain what-if", a ranked list of cells sized to crew
  capacity (30 basins per crew per day), with matching map markers.
- **Evidence on every item:** factor bars that explain each score in plain words, and the 311
  ticket IDs behind every recommendation.
- **Backlog:** open storm-related 311 cases ranked by priority. Cases with no crew note show
  "Status unclear".
- **Backtest:** hit rates on 3 past storms against random and "most past complaints", with
  sample sizes.
- **Heavy-rain trend:** heavy-rain days per year at Logan.

Every recommendation cites at least one 311 ticket ID, every score is the sum of named
factors, every number comes from code, and the app runs without AI.

## Our strategy

We had a short build window and four people, so we designed the Kiro workflow before
writing code:

1. **Steering first.** Three always-on steering files set the product rules, the tech rules
   and folder ownership, so every chat, spec task and sub-agent follows the same rules.
2. **One shared setup.** C prepared the shared pieces once (raw data, cell grid, Makefile,
   pinned dependencies, Dockerfile), and the shared data models live in `contracts/`.
3. **One spec per person, in parallel.** Each person ran their own spec in their own folder.
   Modules connect only through files in `data/demo/` or over HTTP, so specs ran at the same
   time without conflicts.
4. **Fixed merge order.** A → B → C → D, so each layer landed on what it depends on.
5. **Automation guards the rules.** Hooks, property tests and read-only custom agents check
   ownership, evidence, factor sums and no future data.

## Kiro tools and features

| Tool or feature | How we used it |
|---|---|
| Kiro IDE: specs | Every module was built from a Requirements-First spec with EARS requirements, a design and linked tasks |
| Kiro IDE: task orchestrator and sub-agents | D's spec ran task by task through `spec-task-execution` sub-agents, up to 5 in parallel per wave; requirement-detailer sub-agents refined all 10 requirements in parallel. C split design writing, MCP verification and agent creation across parallel sub-agents |
| Kiro IDE: vibe chat | Exploring six unfamiliar data files, the go/no-go data check, setup and steering edits, debugging failed Verify commands |
| Agent hooks | Three hooks: module-ownership guard, citation check, backend tests on stop |
| Custom agents | Two read-only agents in `.kiro/agents/`: a PR reviewer and a contract checker |
| MCP | Our own `drainfast-data` server, used by Kiro in the IDE and the CLI, and sharing code with the API |
| Kiro CLI | `kiro-cli` 2.34.0 in non-interactive mode to run `make test` and to query the MCP server |
| Kiro powers | Not used |

## Steering

`.kiro/steering/` holds three files, all `inclusion: always`:

- **product.md:** the users, what V1 must do, and product rules that can never be broken:
  storm-related reports only, every item cites a ticket, every score shows its breakdown,
  results reported even when worse than a baseline, plain language, the app works without AI.
- **tech.md:** the stack and hard rules: numbers come from code, never an LLM; no data dated
  on or after a test storm is used for features or training; `random_state=42` and ties
  broken by `cell_id`; `DRAINFAST_FALLBACK=1` turns off all AI; no hard-coded secrets; cells
  come only from `contracts/cells.py`; MCP tools and API endpoints call the same Python
  functions. It links the shared models with `#[[file:contracts/schemas.py]]`.
- **structure.md:** the folder layout, one owner per folder, the one-way dependency chain
  (contracts ← data_pipeline ← model ← backend ← frontend), and the git workflow.

**The strategy that made the biggest difference:** writing rules as things Kiro must refuse
or stop for, then backing the most important one with a hook.

- "Only change files inside your module; if a task needs another module, stop and say so."
  Kiro stopped and asked before touching contracts, another owner's folder or `main`, and
  merged C's existing setup branch instead of writing duplicate setup files. C then turned
  this rule into the `c-module-guard` hook, so it is checked before every write, not only
  remembered.
- "Every number shown to users comes from code." When asked to fill in the human hand check
  of labels, Kiro refused, because copying its own labels would produce a fake accuracy. It
  locked the sample with `TODO` placeholders instead.
- "Training data must be strictly before the storm." Kiro used this rule to find leaks the
  plan text did not spell out. B's backtest keeps training storms from overlapping the
  held-out storm's 2-day report window, and leaves storms after the last report day out of
  training so they do not become false "no clog" examples.

Changing one steering line changed every later session. Setup edited steering through Kiro
chat ("All pipeline outputs go to data/demo/. Grid cells come from contracts/cells.py; never
redefine the grid. model exposes score_cells(as_of, rain_in, high_tide).") and every
module after that followed it.

## Spec-driven development

| Spec | Owner | Builds |
|---|---|---|
| `shared-contracts` | team | Enums and Pydantic v2 models every module imports: Report, Cell, Storm, FactorContribution, BriefItem, BriefResponse, BacklogItem, BacktestResult, RainTrendPoint |
| `01-ingest-and-labels` | A | 311 ingest, crew-note cleaning, ordered rule labels, AI labels with fallback, hand-check tooling |
| `01b-cells-and-flags` | A | Grid cells, basin count and owner, EJ flag, flood-area flag |
| `02-risk-model-backtest` | B | Storm days, tide threshold, rain trend, features, logistic regression, 3-storm backtest |
| `03-backend-mcp` | C | Forecast, tide and history sources, priority score, FastAPI endpoints, MCP server |
| `local-dev-macos` | D | React + Vite + Leaflet dashboard, API client with fixture fallback, dev proxy, local run scripts |

**How we structured each spec.** Each feature prompt was complete and specific: input files
and columns, output files and schemas, rule order, edge cases, and the property tests to
include. Each ended with a **Check**, the one requirement that must not be lost, and a
**Verify**, the commands that prove it works:

| Spec | Check | Verify |
|---|---|---|
| 01 | Negative rules come first; the AI is used only for unclear notes | `DRAINFAST_FALLBACK=1 make data` |
| 01b | Every report's cell exists | `make cells`; the flood area must sit on Boston, not in the ocean |
| 02 | "Only reports opened strictly before as_of" is an explicit requirement | `make model`, `make backtest-quick` |
| 03 | Both fallback paths, and score equals the sum of factors | `make api`, then `DRAINFAST_FALLBACK=1 make api` |
| frontend | An item with no evidence never renders | the dashboard on fixture data, then against the live API |

We confirmed each Check appears as an explicit acceptance criterion before running tasks.
Failed Verify output went back into the same chat for Kiro to fix.

**Spec vs vibe coding.** Vibe chat was the right tool for exploring: reading the raw data,
and the go/no-go check (are there enough tickets whose crew note shows a basin was cleaned?
Yes: about 1,500). Specs were the right tool for rules that are easy to get subtly wrong.
In spec 01, label rules run in a fixed order, so "cleaned CB, CB taking water" is
`unclear`, not `clogged_basin`; every dropped row has a named reason and kept + dropped
equals the input; every output row validates against the shared `Report` model. In vibe
mode those rules live in someone's head; in a spec they are numbered requirements with tests
linked to them.

## Property-based testing

60 Python tests pass offline (A 25, B 10, C 25), including Hypothesis property tests tied
to requirements:

| Module | Properties |
|---|---|
| A data | Every label is one of the four values; the same note always gets the same label; the AI is asked only about notes no rule decides; rows are dropped only for logged reasons; identical coordinates give the same `cell_id`; every report's cell exists |
| B model | Adding reports dated on or after `as_of` never changes the features; identical inputs give identical rankings; hit rates are between 0 and 1 |
| C backend | `priority_score` equals the sum of its factors; every brief and backlog item has evidence; rankings do not change when inputs are shuffled; no future data; the brief never exceeds crew capacity |

The shared Pydantic models enforce the same rules at every boundary: a brief item with no
evidence, or a score that differs from the sum of its factors, is rejected.

**What the tests caught.** C's tests found that the filter dropping rain terms from the
backlog also matched "drain" inside "Past clogged-drain reports"; a word-boundary regex
fixed it. A daylight-saving test showed that one hour of a 12-hour NWS forecast block fell
on the previous day; the code was right and the test expectation was fixed. PBT fits these
rules because they must hold for all inputs: the no-future-data property adds random later
reports and checks that nothing changes, which is exactly how a leak would happen.

**What checking real data caught.** Kiro found that the Logan rain file repeats rain in
special reports and duplicate rows (2023-07-29 read 2.61 in raw and 1.89 in after
de-duplication, and 2 false storm days disappeared), and that 3 re-closed 311 cases repeat
the "Case Closed … Case Resolved" system text inside the crew note. Both are fixed in the
pipeline.

## Agent hooks

| Hook | Trigger | What it does |
|---|---|---|
| `c-module-guard` | PreToolUse on file writes | Before any write, checks the path against structure.md and stops edits to frozen contracts or another owner's module |
| `c-citation-check` | PostFileSave on `backend/*.py` | Runs the evidence property tests, so a change that drops ticket evidence fails the moment the file is saved |
| `c-backend-tests-on-stop` | Stop | When an agent run ends with uncommitted backend changes, runs the backend tests offline in fallback mode |

The guard hook turns our most important collaboration rule into a check that runs on every
write. The citation hook guards our most important product rule. The stop hook means no
agent run finishes with broken backend tests unnoticed.

## Custom agents

C used Kiro's custom-agent-creator to build two read-only agents in `.kiro/agents/`:
- `drainfast-pr-reviewer`: run before each merge; reviews the branch against `origin/main`
  for ownership, frozen contracts, no leakage, determinism, fallback, evidence and factor-sum
  rules, and returns "approve" or "changes needed" with file and line.
- `drainfast-contract-checker`: checks that the API's endpoints and responses match the
  contract, and that the `data/demo/` files validate against `contracts.schemas`.

Both may only read and run tests; they can never edit, commit or push.

## MCP

C built `mcp_server/server.py` with the official MCP Python SDK and registered it in
`.kiro/settings/mcp.json` as `drainfast-data`, with its three tools auto-approved:

- `rain_forecast(date)`: National Weather Service precipitation for Boston, in inches for
  that local day.
- `tide_outlook(date)`: NOAA CO-OPS predictions for station 8443970, flagged when the high
  tide exceeds our historical threshold (12.177 ft MLLW).
- `cell_history(cell_id)`: a cell's 311 reports, newest first, with counts.

The tools call the same functions in `backend/sources.py` as the API, so Kiro and the app
see the same numbers. During development we asked Kiro "Using drainfast-data, what's
tomorrow's rain forecast and tide outlook?" and checked live NWS and NOAA data from inside
the editor without writing a script or opening the app. Every tool returns `fallback=true`
instead of failing when the network is down.

## Kiro CLI

C ran `kiro-cli` 2.34.0 in non-interactive mode for two checks: `make test` and the MCP
forecast and tide question. The CLI loaded `.kiro/settings/mcp.json` automatically, so the
same `drainfast-data` server was available in the terminal with no setup. The difference
from the IDE: with `--trust-all-tools` there are no approval prompts and no chat panel, so
every constraint ("do not modify files") must be in the prompt. The CLI suits scripted
checks before a merge; the IDE suits specs and reviewing diffs. Transcripts are in
`docs/build-log/c.md`.

## AI with a fallback

The only AI step labels crew notes that the keyword rules cannot decide, using Amazon
Bedrock's Converse API. The answer must be exactly one of the four labels, or the note stays
`unclear`. Answers are cached, the pipeline never fails because of the AI step, and
`DRAINFAST_FALLBACK=1` turns it off completely. The Docker image sets
`DRAINFAST_FALLBACK=1`, and the labels in our results come from the rules alone.

## Results

- **Data:** 7,313 storm-related 311 tickets, 7,269 kept after removing placeholders and rows
  with no location. Rule labels: 1,527 clogged basin, 177 grading or capacity, 7 coastal
  tide, 5,558 unclear (3,557 have no crew note, mostly open cases).
- **Cells:** 8,818 cells holding 40,815 catch basins and the reports.
- **Rain:** 143 storm days (1 inch or more at Logan) from 2012 to 2026, +0.9 heavy-rain days
  per decade over 2012–2025.
- **Model:** trained on 138 storms, 1,216,884 (storm, cell) rows, 420 positive.
- **Backtest** (8,818 cells; share of each storm's cleaning-fixable reports in our top 100 /
  top 200):

| Storm | Reports | DrainFast | Most past complaints | Random |
|---|---|---|---|---|
| 2023-07-29 | 12 | 16.7% / 33.3% | 16.7% / 25.0% | 1.2% / 2.1% |
| 2023-08-18 | 11 | 9.1% / 27.3% | 9.1% / 9.1% | 1.0% / 2.4% |
| 2024-01-09 | 17 | 29.4% / 47.1% | 11.8% / 17.6% | 1.1% / 2.4% |
| Pooled | 40 | 20.0% / 37.5% | 12.5% / 17.5% | 1.1% / 2.3% |

DrainFast ties or beats "most past complaints" on every storm and beats random by far. With
40 reports, treat the gap over "most past complaints" as encouraging, not proven.

## Honest limits

- DrainFast targets flooding a clogged drain causes, not rain too heavy for any drain.
- Rain, tide and leaf season are the same for every cell on a given day, so they raise all
  scores equally; the ranking comes from each cell's report history.
- 311 reflects who reports, so quiet neighborhoods can look safe. The backlog includes open
  cases, and every cell carries an environmental justice flag.
- Labels depend on crew notes, and many cases have none.
- One rain gauge at Logan Airport stands in for the whole city.
- Real-world impact needs a storm-season pilot with BWSC before any claim.
