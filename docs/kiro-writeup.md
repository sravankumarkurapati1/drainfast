# How we used Kiro to build DrainFast

**Track:** Climate Tech (Hackachusetts C1, resilient communities)
**Team:** A data and labels · B model and backtest · C backend, MCP and setup (lead) · D frontend and live link

## What DrainFast is

Boston has more than 30,000 catch basins, and BWSC crews clean about 60 a day. DrainFast
tells crew supervisors which places to clear first before a storm. It ranks ~100 m grid
cells by how likely they are to have flooding that clearing a catch basin would fix, using
Boston 311 tickets, Logan Airport rainfall, NOAA tides, BWSC catch basin locations,
environmental justice block groups and the Climate Ready Boston flood map.

The app has one screen:
- **Crew brief:** for a date (tomorrow's forecast or a past storm) and a number of crews, a
  ranked list of cells sized to crew capacity (30 basins per crew per day by default).
- **Backlog:** open storm-related 311 cases ranked by priority. Cases with no crew note show
  "Status unclear".
- **Evidence panel:** factor bars that explain each score, basin count and owner, EJ and
  flood-area badges, cell history, and links to the 311 tickets behind every item.
- **Backtest:** hit rates on 3 past storms against random and "most past complaints".
- **Heavy-rain trend:** heavy-rain days per year at Logan.

Every recommendation cites at least one 311 ticket ID, every score is the sum of named
factors, every number comes from code, and the app works fully without AI.

## Our strategy

We had two hours and four people, so we designed the Kiro workflow before writing code:

1. **Steering first.** Three always-on steering files set the product rules, the tech rules
   and folder ownership, so every chat and every spec task follows the same rules.
2. **One shared setup.** C prepared the shared pieces once (data, cell grid, Makefile,
   dependencies, Dockerfile), so nobody redefines them.
3. **One spec per person, in parallel.** Each person ran their own spec in their own folder.
   Modules connect only through files in `data/demo/` or over HTTP, so specs can run at the
   same time without conflicts.
4. **Fixed merge order.** A → B → C → D, so each layer lands on what it depends on.
5. **Hooks and tests guard the rules** that matter most: no future data in the model,
   evidence on every item, scores equal to the sum of their factors.

## Kiro tools

| Tool | How we used it |
|---|---|
| Kiro IDE: spec workflow | Every module was built from a spec (Quick Spec, or Requirements-First approved phase by phase), with "Run all tasks" running independent tasks in parallel |
| Kiro IDE: vibe chat | Exploring the raw data, the go/no-go data check, setup edits, steering edits, debugging failed Verify commands |
| Kiro IDE: agent hooks | A backtest hook and a citation-check hook |
| Kiro IDE: MCP | Our own `drainfast-data` MCP server, used by both Kiro and the app |
| Kiro CLI | Running `make test` from the terminal, compared with running it in the IDE |

## Steering

`.kiro/steering/` holds three files, all `inclusion: always`:

- **product.md:** who the users are, what V1 must do, and product rules that can never be
  broken: storm-related reports only, every item cites a ticket, every score shows its
  breakdown, results reported even when worse than a baseline, plain language, the app works
  without AI.
- **tech.md:** the stack and hard rules: numbers come from code, never the LLM; no data
  dated on or after a test storm is used for features or training; `random_state=42` and
  ties broken by `cell_id`; `DRAINFAST_FALLBACK=1` turns off all AI; no hard-coded secrets;
  cells come only from `contracts/cells.py`; MCP tools and API endpoints call the same
  Python functions.
- **structure.md:** the folder layout, one owner per folder, the one-way dependency chain
  (contracts ← data_pipeline ← model ← backend ← frontend), and the git workflow.

tech.md links the shared contracts with `#[[file:contracts/openapi.yaml]]` and
`#[[file:contracts/schemas.py]]`, so Kiro always sees the real data shapes and API.

**The strategy that made the biggest difference:** writing rules as things Kiro must refuse
or stop for. "Only change files inside your module; if a task needs another module, stop and
say so" kept four parallel sessions from editing each other's code. "Every number shown to
users comes from code" stopped Kiro from inventing numbers: when asked to fill in the human
hand check, it refused and locked the sample with `TODO` placeholders instead. "Training data
must be strictly before the storm" made Kiro catch a subtle leak: a report opened before a
storm may only get its crew note, and so its label, after the storm.

Setup also used Kiro chat to edit steering, for example: "All pipeline outputs go to
data/demo/. Grid cells come from contracts/cells.py; never redefine the grid. model exposes
score_cells(as_of, rain_in, high_tide)." Changing one steering line changed every later
session.

## Spec-driven development

| Spec | Owner | Builds |
|---|---|---|
| `shared-contracts` | team | Enums and Pydantic models every module imports: Report, Cell, Storm, FactorContribution, BriefItem, BriefResponse, BacklogItem, BacktestResult, RainTrendPoint |
| `01-ingest-and-labels` | A | 311 ingest, crew-note cleaning, rule labels, AI labels with fallback, 50-ticket hand check |
| `01b-cells-and-flags` | A | Grid cells, basin count and owner, EJ flag, flood-area flag |
| `02-risk-model-backtest` | B | Storm days, tide threshold, rain trend, features, logistic regression, 3-storm backtest |
| `03-backend-mcp` | C | Forecast, tide and history sources, priority score, FastAPI endpoints, MCP server |
| `04-frontend` | D | React + Leaflet app: brief, backlog, evidence panel, backtest, rain trend |

**How we structured each spec.** The feature prompt for each spec is complete and specific:
input files and columns, output files and schemas, rule order, edge cases, and the property
tests to include. Each prompt ends with a **Check**, the one requirement that must not be
lost, and a **Verify**, the commands that prove it works:

| Spec | Check | Verify |
|---|---|---|
| 01 | Negative rules come first; the AI is used only for unclear notes | `DRAINFAST_FALLBACK=1 make data` |
| 01b | Every report's cell exists | `make cells`, then the flood area must sit on Boston, not in the ocean |
| 02 | "Only reports opened strictly before as_of" is an explicit requirement | `make model`, `make backtest-quick` |
| 03 | Both fallback paths, and score equals the sum of factors | `make api`, then `DRAINFAST_FALLBACK=1 make api` |
| 04 | An item with no evidence never renders | `make web` shows every tab on fixture data |

After Kiro generated requirements, each person spent two minutes confirming the Check
appears as an explicit acceptance criterion, kept every property-test task, and ran all
tasks. Failed Verify output went back into the same chat for Kiro to fix.

**Spec vs vibe coding.** Vibe chat was the right tool for exploring: reading six unfamiliar
data files, the go/no-go check (are there enough tickets whose crew note shows a basin was
cleaned? Yes: about 1,500), and one-off edits. Specs were the right tool for anything with
rules that are easy to get subtly wrong. Examples from spec 01: label rules run in a fixed
order, so "cleaned CB, CB taking water" is `unclear`, not `clogged_basin`; every dropped row
has a named reason and kept + dropped equals the input; every output row validates against
the shared `Report` model. In vibe mode those rules live in someone's head; in a spec they
are numbered requirements with tests linked to them.

## Property-based testing

Every spec includes Hypothesis property tests tied to its requirements:

| Spec | Properties |
|---|---|
| shared-contracts | Every model survives a JSON round trip; unknown fields, blank IDs and out-of-range numbers are rejected; a brief item with no evidence is rejected; a score that differs from the sum of its factors is rejected |
| 01 | Every label is one of the four values; the same note always gets the same label; the AI is asked only about notes no rule decides; rows are dropped only for logged reasons |
| 01b | Identical coordinates give the same `cell_id`; every report's cell exists |
| 02 | Adding reports dated on or after `as_of` never changes the features (no future data); identical inputs give identical rankings; hit rates are between 0 and 1 |
| 03 | `priority_score` equals the sum of its factors; every brief and backlog item has at least one evidence ticket; identical inputs give identical rankings |

PBT fits these requirements because they are rules over all inputs, not single examples.
A unit test checks that one example note gets one label. A property test generates hundreds
of notes, including empty strings, odd capitalization, HTML entities and mixed keywords, and
checks that every one gets a valid label. The no-future-data property is the clearest case:
it adds random later reports and checks that nothing changes, which is how a leak would
actually happen.

Generated inputs include real edge cases from the data, such as daylight-saving hours in
November and March, and malformed coordinates and dates.

## Agent hooks

| Hook | Trigger | What it does |
|---|---|---|
| `.kiro/hooks/b-backtest-quick.json` | Post Task Execution | After any spec task that changes `model/`, runs `make backtest-quick` and reports the top-100 hit rate |
| `.kiro/hooks/c-citation-check.json` | PostFileSave on `backend/*.py` | Runs `pytest tests/backend -q -k evidence`, the property tests that require evidence on every item |

The backtest hook turns "did that change make the model better or worse?" into an automatic
answer after every task, and it runs in under 30 seconds on one storm. The citation hook
guards our most important product rule: if a backend change ever lets an item through
without ticket evidence, the test fails the moment the file is saved.

## MCP

C built `mcp_server/server.py` with the official MCP Python SDK and registered it in
`.kiro/settings/mcp.json` as `drainfast-data`. It exposes three tools:

- `rain_forecast(date)`: National Weather Service quantitative precipitation for Boston,
  converted to inches for that local day.
- `tide_outlook(date)`: NOAA CO-OPS predictions for station 8443970, flagged when the high
  tide exceeds our historical threshold.
- `cell_history(cell_id)`: a cell's 311 reports, newest first, with counts.

The tools call the same functions in `backend/sources.py` as the API, so Kiro, the co-pilot
and the app always see the same numbers. During development this let us ask Kiro "Using
drainfast-data, what's tomorrow's rain forecast and tide outlook?" and check live forecast
and tide data from inside the IDE, without writing a test script or opening the app. Every
tool returns `fallback=true` instead of failing when the network is down.

## Kiro CLI

We ran `make test` once through the Kiro CLI, alongside the IDE runs, to compare a
terminal-first workflow with the IDE.

## AI with a fallback

The only AI step labels crew notes that the keyword rules cannot decide, using Amazon
Bedrock's Converse API. Its answer must be exactly one of the four labels, or the note stays
`unclear`. Answers are cached, the pipeline never fails because of the AI step, and
`DRAINFAST_FALLBACK=1` turns it off completely. The deployed app runs in fallback mode, so
judges always see results that come only from code.

## Results

- **Data:** 7,313 storm-related 311 tickets, 7,269 kept after removing placeholders and rows
  with no location. Rule labels: 1,527 clogged basin, 177 grading or capacity, 7 coastal
  tide, 5,558 unclear (3,557 have no crew note, mostly open cases).
- **Cells:** 8,818 cells holding 40,815 catch basins and the reports.
- **Rain:** 143 storm days (1 inch or more at Logan) from 2012 to 2026.
- **Label accuracy (50-ticket hand check):** ___
- **Backtest (3 storms since 2023, top 100 / top 200):** DrainFast ___ · most past
  complaints ___ · random ___. The test storms are 2024-01-09, 2023-07-29 and 2025-03-17,
  with 17, 12 and 11 cleaning-fixable reports, so we report sample sizes with every number.

## Honest limits

- DrainFast targets flooding a clogged drain causes, not rain too heavy for any drain.
- 311 reflects who reports, so quiet neighborhoods can look safe. The backlog includes open
  cases, and every cell carries an environmental justice flag.
- Labels depend on crew notes, and many cases have none.
- One rain gauge at Logan Airport stands in for the whole city.
- Real-world impact needs a storm-season pilot with BWSC before any claim.
