# Requirements Document: 01-ingest-and-labels

## Introduction

Member A's first spec. `python -m data_pipeline.run` turns the raw Boston 311 export
(`data/raw/311/boston_311_catchbasin_flooding.csv`) into `data/demo/reports.parquet`
(one row per `contracts.schemas.Report`) and `data/demo/hand_check.csv`.
`python -m data_pipeline.run --score` turns a filled hand check into
`data/demo/label_accuracy.json`. Downstream, the model (B) predicts cells with
`clogged_basin` reports and the backend (C) reuses `label_report(text)`.

## Glossary

- **Crew note**: the part of `closure_reason` left after removing the "Case Closed"
  prefix, the closed-date timestamp and the status phrase.
- **Status phrase**: one of Case Resolved, Case Noted, Case Invalid, Case Referred to
  External Agency, Duplicate of Existing Case, Resolved, Noted.
- **Blank note**: a crew note that is empty after cleaning (`note_blank = true`).
- **Excluded note**: a note or status that mentions test, invalid, error, wrong e-form
  or duplicate (`exclude = true`).
- **Undecided note**: a non-blank, non-excluded note that matches no rule group.
- **Fallback mode**: `DRAINFAST_FALLBACK=1`.

## Requirements

### Requirement 1: Read and clean the 311 export

**User Story:** As the model owner, I want clean, typed report rows, so that features
are built from trustworthy data.

#### Acceptance Criteria

1. WHEN the pipeline reads the CSV, THE pipeline SHALL map `ticket_id` = `case_enquiry_id`
   (string), `opened_at` = `open_dt`, `closed_at` = `closed_dt`, `status` = lower-case
   `case_status`, `lat` = `latitude`, `lon` = `longitude`, `text` = `case_title`, and
   `neighborhood`.
2. THE pipeline SHALL parse `open_dt` and `closed_dt` in their mixed formats as local
   America/New_York times and store timezone-aware timestamps.
3. THE pipeline SHALL unescape HTML entities (for example `&amp;`) in all text fields.
4. WHEN a row has missing or non-numeric coordinates, THE pipeline SHALL drop it with
   reason `missing_coordinates`.
5. WHEN a row's location is "1 City Hall Plz" (a placeholder), THE pipeline SHALL drop
   it with reason `city_hall_placeholder`.
6. WHEN a row cannot become a valid Report (unparseable `open_dt`, unknown status, or
   `closed_at` before `opened_at`), THE pipeline SHALL drop it with a named reason.
7. THE pipeline SHALL log the count of dropped rows per reason, and kept rows plus
   dropped rows SHALL equal the input row count.
8. WHEN `neighborhood` is blank, THE pipeline SHALL store "Unknown".
9. THE pipeline SHALL set `status = open` rows' `closed_at` to null.

### Requirement 2: Crew notes

**User Story:** As a crew supervisor, I want the crew's own words separated from system
text, so that labels reflect what the crew did.

#### Acceptance Criteria

1. THE pipeline SHALL remove the prefix "Case Closed. Closed date : <timestamp> " or
   "Case Closed ", in both ISO and "Tue Oct 21 10:00:00 EDT 2014" timestamp forms.
2. THE pipeline SHALL then remove a leading status phrase.
3. THE pipeline SHALL set `note_blank = true` when nothing remains, and store
   `closing_note` as null in that case.
4. THE pipeline SHALL set `exclude = true` when the note or status phrase mentions test,
   invalid, error, wrong e-form or duplicate.

### Requirement 3: Rule labels

**User Story:** As the model owner, I want deterministic cause labels, so that the
target "cleaning-fixable" is reproducible.

#### Acceptance Criteria

1. THE rules SHALL live in `data_pipeline/label_rules.yaml` and be checked in this
   order, first match wins:
   a) unclear: takes water, taking water, no cleaning needed, no flooding, not blocked,
      clear on arrival;
   b) grading_capacity: grading, pitch, ponding, low spot, no catch basin, private,
      not bwsc, pwd, construction;
   c) coastal_tide: tide, tidal, coastal;
   d) clogged_basin: clean, clear, debris, leaves, vactor, jet, flush, relieved flood,
      removed.
2. **Check:** THE negative rules (a, b) SHALL be checked before clogged_basin, so a note
   such as "cleaned, takes water" is labeled `unclear`.
3. WHEN no rule matches, THE label SHALL be `unclear`.
4. Blank and excluded notes SHALL be labeled `unclear` with `label_source = rule`.
5. Rule-decided labels SHALL have `label_source = rule`.
6. Every label SHALL be one of `clogged_basin`, `grading_capacity`, `coastal_tide`,
   `unclear`.
7. THE same note SHALL always receive the same label.

### Requirement 4: AI labels with fallback

**User Story:** As the team, I want AI help only where rules cannot decide, and an app
that never depends on it.

#### Acceptance Criteria

1. **Check:** THE pipeline SHALL call Amazon Bedrock only for undecided notes (non-blank,
   non-excluded, no rule match).
2. WHEN fallback mode is on, THE pipeline SHALL make no Bedrock calls.
3. THE pipeline SHALL use the boto3 `bedrock-runtime` Converse API with the model from
   `BEDROCK_MODEL_ID`, and read region and profile from `AWS_REGION` and `AWS_PROFILE`.
4. WHEN Bedrock answers exactly one of the four labels, THE pipeline SHALL use it with
   `label_source = llm`.
5. WHEN Bedrock answers anything else or raises an error, THE label SHALL be `unclear`
   with `label_source = rule`.
6. THE pipeline SHALL cache valid answers in `data/demo/llm_cache.json` and SHALL never
   fail because of the AI step.
7. THE prompt SHALL live in a `.txt` file next to the code.

### Requirement 5: Cells, flags and output

#### Acceptance Criteria

1. THE pipeline SHALL set `cell_id = contracts.cells.cell_id(lat, lon)` and never
   redefine the grid.
2. THE pipeline SHALL set `ej_flag` true when the report point lies in any polygon of
   `data/raw/ej/ej_block_groups_boston.geojson`.
3. THE pipeline SHALL write `data/demo/reports.parquet` with the Report fields
   (`storm_day` and `duplicate_of` null) plus the `exclude` column.
4. WHEN `contracts.schemas` is available, THE pipeline SHALL validate every row as a
   `Report` and fail loudly on an invalid row.

### Requirement 6: Hand check

#### Acceptance Criteria

1. THE pipeline SHALL write 50 non-blank, non-excluded rows, sampled with seed 42, to
   `data/demo/hand_check.csv` with an empty `human_label` column.
2. WHEN `hand_check.csv` already has any `human_label` filled, THE pipeline SHALL NOT
   overwrite it.
3. `python -m data_pipeline.run --score` SHALL read the filled file and write
   `data/demo/label_accuracy.json` with accuracy overall and by `label_source`, with
   sample sizes.

### Requirement 7: Summary

1. THE pipeline SHALL print rows kept and dropped (per reason), blank notes, and counts
   per label and per label source.

### Requirement 8: Property tests

1. Hypothesis tests SHALL check: every label is one of the four values; the same note
   always gets the same label; rows are dropped only for logged reasons; the AI is
   called only for undecided notes.
