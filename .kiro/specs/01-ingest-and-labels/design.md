# Design Document: 01-ingest-and-labels

## Overview

A small, pure-function pipeline in `data_pipeline/`. Each step takes a DataFrame or a
string and returns a new value, so each one is testable on its own. Only `run.py`
reads and writes files.

```
CSV ──ingest.load_raw──> raw df ──ingest.clean_reports──> kept df + drop counts
        notes.split_closure ─> closing_note, status_phrase, note_blank, exclude
        labeler.label_note  ─> cause_label, label_source   (rules, then optional LLM)
        contracts.cells.cell_id ─> cell_id
        geo.points_in_area(EJ) ─> ej_flag
run.py ─> data/demo/reports.parquet, data/demo/hand_check.csv, summary
run.py --score ─> data/demo/label_accuracy.json
```

## Components

| File | Responsibility |
|---|---|
| `paths.py` | Input and output paths, derived from the project root. Swap to `contracts.paths` once it exists. |
| `notes.py` | `split_closure(text) -> (note, status_phrase)`, `is_excluded(note, status)`. Regex only, no I/O. |
| `label_rules.yaml` | Ordered rule groups: unclear, grading_capacity, coastal_tide, clogged_basin. |
| `labeler.py` | `load_rules()`, `rule_label(note)`, `label_note(note, exclude, llm)`, and the public `label_report(text)` for the backend. |
| `llm.py`, `label_prompt.txt` | `BedrockLabeler`: Converse API call, answer validation, JSON cache, circuit breaker after repeated errors. |
| `geo.py` | `load_polygons(geojson)`, `points_in_area(area, lats, lons)` with `shapely.contains_xy`. |
| `ingest.py` | `load_raw(path)`, `clean_reports(df, ej_area, labeler) -> (reports, drops)`. |
| `handcheck.py` | `sample_hand_check(reports)`, `score_hand_check(df)`. |
| `run.py` | CLI entry point: build, write, print summary; `--score`. |

## Key decisions

- **Rule matching**: text is HTML-unescaped, lower-cased, curly quotes normalized and
  whitespace collapsed. A keyword matches at a word start (`\bclean` matches
  "cleaned" but `\bclear` does not match "unclear"). Groups are checked in file order;
  first match wins, so negative groups beat `clogged_basin`.
- **What the LLM sees**: only notes with no rule match. Notes matched by the negative
  `unclear` group (for example "takes water") are decided and never sent, so the AI
  cannot overturn a negative rule.
- **LLM safety**: no call when `DRAINFAST_FALLBACK=1` or `BEDROCK_MODEL_ID` is empty.
  After 3 consecutive errors the labeler stops calling for the rest of the run. Any
  invalid answer becomes `unclear` / `rule`. Valid answers are cached by note text.
- **Timestamps**: `pd.to_datetime(format="mixed")`, then localize to America/New_York.
  Ambiguous fall-back hours are read as standard time and missing spring-forward hours
  shift forward, so no row is lost to DST.
- **Placeholders**: rows whose location is "1 City Hall Plz" are dropped. Their
  coordinates are City Hall's, so they would create a false hot spot.
- **Output**: Report fields plus `exclude`, sorted by `ticket_id`, written with an
  explicit pyarrow schema. When `contracts.schemas` exists, every row is validated as a
  `Report` (the `exclude` column is checked separately because Report forbids extra
  fields).
- **Determinism**: no use of today's date; hand-check sample uses seed 42.

## Error handling

- Drop reasons: `missing_coordinates`, `city_hall_placeholder`, `bad_open_dt`,
  `unknown_status`, `closed_before_opened`. Kept + dropped always equals input.
- The LLM step never raises out of `label_note`.
- `--score` fails with a clear message when `hand_check.csv` is missing, unfilled, or
  holds a label outside the four values.

## Testing strategy

Hypothesis property tests in `tests/data_pipeline/` (offline, `DRAINFAST_FALLBACK=1`,
sockets blocked):

1. Every label is one of the four values, for any text.
2. The same note always gets the same label.
3. Rows are dropped only for the named reasons, and kept + dropped = input.
4. The LLM is called only for undecided notes, and an invalid answer gives `unclear`.

Unit tests cover the prefix formats, the negative-rules-first example, and HTML
unescaping.
