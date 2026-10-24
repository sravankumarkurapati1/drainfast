---
inclusion: always
---
# DrainFast — Product Overview

## One line
DrainFast tells Boston's crews which catch basins to clear before a storm, with every
recommendation backed by real past 311 tickets.

## The problem
- Boston has more than 30,000 catch basins. BWSC crews clean about 60 a day, so they
  cannot clear every basin before a storm.
- Today crews rely on residents' calls. The same places flood storm after storm, and
  leaf season (October to November) is the worst time for clogged grates.

## Users
BWSC crew supervisors and Boston 311 staff: busy operations staff who need short
answers, a clear reason for every recommendation, and evidence they can check.

## Versions
The app is one screen with three tabs: Before, During, After.

### V1 — Before the storm (current build, must ship)
- Crew brief: for a chosen date (tomorrow's forecast or a past storm date) and a chosen
  number of crews, a ranked list of cells to clear first. The list length follows crew
  capacity (configurable, default 30 basins per crew per day).
- Backlog: open storm-related 311 cases ranked by priority. Cases with a blank crew
  note show "Status unclear".
- Priority score with a visible breakdown: every ranked item shows which factors
  raised its score and by how much.
- Evidence panel: each item shows its reason, cell history, and the past 311 ticket
  IDs behind it.
- Backtest: on 3 past storms, compared with random and "most past complaints", with
  sample sizes shown.
- Heavy-rain trend chart: heavy-rain days per year at Boston Logan.

### V2 — During the storm (later)
Reuses V1's labels, cell history and score to triage incoming reports.

### V3 — After the storm (later)
Reuses V1's brief and V2's storm results for summaries and reporting.

### Co-pilot (across all versions)
Answers questions by calling the same MCP tools the app uses. It explains results and
never produces a number that did not come from a tool.

Do not build V2 or V3 features until V1 is done. The During and After tabs show
"Coming soon" in V1.

## Key definitions
- Cell: a roughly 100 m grid square. All history, scores and rankings are per cell.
- Cleaning-fixable flood: a report whose crew note shows that clearing a catch basin
  resolved it. This is what the model predicts.
- Storm day: a day with 1 inch or more of rain at Boston Logan.
- Evidence: the 311 ticket IDs a result is based on.
- Status unclear: an open or closed case whose crew note is blank.

## Product rules (never break these)
1. Scope: storm-related reports only (flooding, catch basins, storm drains).
2. Evidence: every brief and backlog item cites at least one 311 ticket ID.
3. Explainable: every score shows its factor breakdown.
4. Honesty: report backtest results with sample sizes, even when worse than a
   baseline. Never claim savings that were not measured.
5. Plain language in all user-facing text ("Likely clogged drain", not "clogged_basin").
6. The app always works in fallback mode, without AI.

## V1 is done when
- The brief works for tomorrow's forecast and for a past storm date.
- Backtest numbers are recorded.
- Fallback mode works.
- The live link works with no login.