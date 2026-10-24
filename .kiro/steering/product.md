---
inclusion: always
---
# DrainFast — Product Overview

## One line
DrainFast tells Boston's crews which catch basins to clear before a storm, and sorts
the flood reports that pour in during it, with every recommendation backed by real
past 311 tickets.

## The problem
- Boston has more than 30,000 catch basins. BWSC crews can clean about 60 a day, so
  they cannot clear every basin before a storm.
- Today the cycle is reactive. Residents report flooding through 311 after it starts.
  Staff notify BWSC by hand, close duplicate reports one by one, and crews learn the
  cause only when they arrive on site.
- The same locations flood storm after storm. Leaf season (October to November) is
  the worst time for clogged grates, and heavy-rain events are increasing.

## Users
- Primary: BWSC crew supervisors, who decide where crews go, and Boston 311 staff,
  who handle incoming reports.
- They are busy operations staff, not data scientists. They need short answers,
  a clear reason for every recommendation, and evidence they can check themselves.

## Core features
### Before the storm: predict
- Pre-storm crew brief: a ranked list of locations most likely to have
  cleaning-fixable flooding, given the National Weather Service rain forecast.
- Each brief item shows its rank, the location, a plain-language reason, and the
  past 311 ticket IDs behind it.

### During the storm: triage incoming reports
- Cause label for each report: likely clogged basin, grading or capacity problem,
  coastal tide issue, or unclear.
- Duplicate merging: group reports of the same flood by meaning, location and time.
- Location history: past floods and cleanings at that spot
  (for example "6 past reports; basin cleaned 4 times").
- Routing suggestion: clogged basins to BWSC; grading or street problems to the
  relevant city department.
- Draft work orders with cause, history, priority and evidence. Staff approve each one.

### After the storm: learn and report
- Prediction check: how many of the storm's cleaning-fixable reports were on the
  previous day's brief.
- Storm summary for managers: counts, locations, likely causes, repeat spots.
- Equity view: time to close by neighborhood, including open cases, plus areas where
  predicted risk is high but reports are few.
- Evidence appendix: cited tables supporting the catch basin section of BWSC's
  annual stormwater report.

### Co-pilot
- A chat panel that answers questions such as "Two inches of rain tomorrow and only
  two crews. Where should they go?" by calling DrainFast's own API.
- It explains results. It never produces a number that did not come from a tool.

## Key definitions
- Cleaning-fixable flood: a report whose crew closing note shows that clearing a
  catch basin resolved it. This is the only outcome the model predicts.
- Evidence: the 311 ticket IDs a result is based on.
- Storm day: a day whose rainfall at Boston Logan meets the storm threshold.
- Location: a roughly 50 m grid cell, or a basin point if basin data is available.

## Product rules (never break these)
1. Scope: storm-related reports only (flooding, catch basins, storm drains).
   Never add general 311 features such as potholes, streetlights, noise or trash.
2. Human in the loop: staff approve every work order. Nothing is sent automatically.
3. Evidence: every brief item, recommendation and work order cites at least one
   past 311 ticket ID.
4. Honesty: report results even when they are worse than a baseline. Show label
   accuracy. Never claim cost or time savings that were not measured.
5. Equity: count open cases, not only closed ones, and flag high-risk areas with
   few reports.
6. Plain language: user-facing text avoids jargon. Show "Likely clogged drain",
   not "clogged_basin".

## How we measure success
- Brief hit rate: share of a held-out storm's cleaning-fixable reports that fall in
  our top 100 and top 200 locations, compared with random and with
  "most past complaints" (the real test).
- Cause labels: agreement with crew closing notes on held-out tickets.
- Duplicate merging: precision and recall against staff-marked duplicates.
- Speed: seconds to process a replayed storm's reports.

## Out of scope for this build
- General 311 complaint handling.
- Sensors or hardware.
- Automatically dispatching crews.
- Small-town stormwater permit reporting and resident text alerts (roadmap only).