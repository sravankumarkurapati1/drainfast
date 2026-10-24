# Requirements Document

## Introduction

The shared contracts are the single source of truth for every data shape, file path and HTTP endpoint in DrainFast. They live in `contracts/` and are frozen: data_pipeline, model, evaluation, backend and frontend import or consume them and never redefine them. This spec covers the V1 scope: the Pydantic v2 schemas (`contracts/schemas.py`), the data path constants (`contracts/paths.py`), the OpenAPI 3.1 document (`contracts/openapi.yaml`), JSON fixtures with realistic Boston examples (`contracts/fixtures/`), and the contract tests (`tests/contracts/`). Only files inside `contracts/` and `tests/contracts/` are created. The V1 Model set is Report, Cell, Storm, FactorContribution, BriefItem, BriefResponse, BacklogItem, BacktestResult and RainTrendPoint. StormSummary, WorkOrder, NeighborhoodEquity, CopilotRequest and CopilotResponse are removed from V1 and return in V2/V3.

## Glossary

- **Contracts_Package**: The Python package at `contracts/` containing `schemas.py`, `paths.py`, `openapi.yaml` and `fixtures/`.
- **Schemas_Module**: The file `contracts/schemas.py` that defines all shared Pydantic v2 models, enums and constants.
- **Paths_Module**: The file `contracts/paths.py` that defines all shared data file path constants.
- **OpenAPI_Document**: The file `contracts/openapi.yaml`, an OpenAPI 3.1 description of the DrainFast HTTP API.
- **Fixture_Set**: The JSON files in `contracts/fixtures/`, one file per model.
- **Contract_Tests**: The pytest test files in `tests/contracts/`.
- **Model**: Any Pydantic v2 class defined in the Schemas_Module (Report, Cell, Storm, FactorContribution, BriefItem, BriefResponse, BacklogItem, BacktestResult, RainTrendPoint).
- **CauseLabel**: String enum with values `clogged_basin`, `grading_capacity`, `coastal_tide`, `unclear`.
- **LabelSource**: String enum with values `rule`, `llm`.
- **ReportStatus**: String enum with values `open`, `closed`.
- **BasinOwner**: String enum with values `BWSC`, `City`, `Private`, `Mixed`, `Unknown`, describing who owns the catch basins in a Cell.
- **Cell**: A grid square of roughly 100 m by 100 m covering part of Boston, identified by a `cell_id`.
- **Evidence**: The list of past 311 ticket IDs a result is based on.
- **Storm_Day**: A calendar date (no time component) whose rainfall at Boston Logan meets the Storm_Day_Threshold.
- **Storm_Day_Threshold**: The minimum daily rainfall total, in inches, for a date to count as a Storm_Day; default 1.0 inch.
- **Factor_Sum**: The sum of the `contribution` values of all FactorContribution entries in a `factors` list.
- **Aware_Datetime**: A datetime carrying timezone information; DrainFast values are in America/New_York.
- **Rate**: A float in the closed range 0.0 to 1.0.
- **Project_Root**: The repository root directory `drainfast/`.
- **Blank_String**: A string that is empty or contains only whitespace characters.
- **Non_Finite_Float**: A float value that is NaN, positive infinity or negative infinity.

## Requirements

### Requirement 1: Enums

**User Story:** As a module developer, I want shared enums for cause labels, statuses and basin owners, so that every module uses the same allowed values.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define CauseLabel as a `str` enum with exactly the values `clogged_basin`, `grading_capacity`, `coastal_tide` and `unclear` and no other values.
2. THE Schemas_Module SHALL define LabelSource as a `str` enum with exactly the values `rule` and `llm` and no other values.
3. THE Schemas_Module SHALL define ReportStatus as a `str` enum with exactly the values `open` and `closed` and no other values.
4. THE Schemas_Module SHALL define BasinOwner as a `str` enum with exactly the values `BWSC`, `City`, `Private`, `Mixed` and `Unknown` and no other values.
5. IF a Model field typed with an enum receives a value outside that enum, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.
6. WHEN a Model field typed with an enum receives a string, THE Schemas_Module SHALL accept the string only if the string matches an enum value exactly, including letter case.
7. IF a Model field typed with an enum receives an empty string, a differently-cased string or a non-string value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.
8. IF a non-optional Model field typed with an enum receives None, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.
9. THE Schemas_Module SHALL serialize every enum field as the plain string value of the enum member.

### Requirement 2: Report model

**User Story:** As a 311 triage developer, I want a single Report model, so that the pipeline, backend and frontend agree on what a flood report contains.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a Report Model with the fields `ticket_id` (str), `opened_at` (Aware_Datetime), `closed_at` (optional Aware_Datetime, default None), `status` (ReportStatus), `lat` (float), `lon` (float), `cell_id` (str), `text` (str), `closing_note` (optional str, default None), `note_blank` (bool), `cause_label` (CauseLabel), `label_source` (LabelSource), `storm_day` (optional date, default None), `neighborhood` (str), `ej_flag` (bool) and `duplicate_of` (optional str, default None).
2. IF a Report receives an `opened_at` or `closed_at` value without timezone information, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a Report receives a `closed_at` value strictly earlier than its `opened_at` value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a Report receives a `lat` outside the inclusive range -90.0 to 90.0 or a `lon` outside the inclusive range -180.0 to 180.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. IF a Report receives a `duplicate_of` value equal to its own `ticket_id`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. THE Schemas_Module SHALL treat every Report field without a default, including `note_blank`, as required.
7. WHEN a Report receives a `closed_at` value equal to its `opened_at` value, THE Schemas_Module SHALL accept the Report.
8. IF a Report receives a `lat` or `lon` that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
9. IF a Report has `status` equal to `open` and a `closed_at` value other than None, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
10. IF a Report receives a Blank_String for `ticket_id`, `cell_id` or `neighborhood`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
11. IF a Report is missing a required field or receives an invalid enum value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.

### Requirement 3: Cell model

**User Story:** As a model developer, I want a shared Cell model, so that rankings and maps refer to the same grid squares.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a Cell Model with the fields `cell_id` (str), `lat` (float), `lon` (float), `neighborhood` (str), `basin_count` (int), `basin_owner` (BasinOwner), `ej_flag` (bool), `flood_area_flag` (bool) and `tree_density` (optional float, default None).
2. THE Schemas_Module SHALL treat every Cell field except `tree_density` as required.
3. IF a Cell receives a Blank_String for `cell_id` or `neighborhood`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a Cell receives a `lat` outside the inclusive range -90.0 to 90.0 or a `lon` outside the inclusive range -180.0 to 180.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. IF a Cell receives a `lat`, `lon` or non-null `tree_density` that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. IF a Cell receives a `basin_count` below 0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
7. IF a Cell receives a non-null `tree_density` below 0.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
8. WHEN a Cell receives a `basin_count` of 0 or a `tree_density` of 0.0, THE Schemas_Module SHALL accept the Cell.
9. IF a Cell is missing a required field or receives an invalid `basin_owner` value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.

### Requirement 4: Storm model and storm-day threshold

**User Story:** As a data developer, I want a shared Storm model and a single storm-day rule, so that storm days are described and selected the same way in every module.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a Storm Model with the fields `storm_day` (date), `rain_total_in` (float), `max_hourly_in` (float) and `high_tide_flag` (bool).
2. IF a Storm receives a `rain_total_in` or `max_hourly_in` value below 0.0, above 30.0 or equal to a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a Storm receives a `max_hourly_in` strictly greater than its `rain_total_in`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. THE Schemas_Module SHALL treat every Storm field as required.
5. WHEN a Storm receives a `max_hourly_in` equal to its `rain_total_in`, THE Schemas_Module SHALL accept the Storm.
6. WHEN a Storm receives a `storm_day` string in ISO calendar date format `YYYY-MM-DD`, THE Schemas_Module SHALL accept the value as a date.
7. IF a Storm receives a `storm_day` datetime with a non-zero time component, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
8. THE Schemas_Module SHALL define a module constant `STORM_DAY_THRESHOLD_IN` equal to the float 1.0, representing the Storm_Day_Threshold.
9. THE Schemas_Module SHALL provide an `is_storm_day` operation on Storm with a `threshold` parameter defaulting to `STORM_DAY_THRESHOLD_IN`.
10. WHEN `is_storm_day` is called, THE Schemas_Module SHALL return True if `rain_total_in` is greater than or equal to `threshold` and False otherwise.
11. WHEN `is_storm_day` is called with the default threshold on a Storm whose `rain_total_in` equals exactly 1.0, THE Schemas_Module SHALL return True.

### Requirement 5: FactorContribution model

**User Story:** As a crew supervisor, I want each priority score broken into named factors, so that I can see what drove a ranking.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a FactorContribution Model with the fields `factor` (str), `value` (float) and `contribution` (float).
2. THE Schemas_Module SHALL treat every FactorContribution field as required.
3. IF a FactorContribution receives a Blank_String for `factor`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a FactorContribution receives a `value` or `contribution` that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. WHEN a FactorContribution receives a negative or zero `contribution`, THE Schemas_Module SHALL accept the FactorContribution.

### Requirement 6: BriefItem model with mandatory evidence

**User Story:** As a crew supervisor, I want every brief item to carry factors and evidence, so that I can check why a cell was recommended.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a BriefItem Model with the fields `rank` (int), `cell_id` (str), `lat` (float), `lon` (float), `priority_score` (float), `factors` (list of FactorContribution), `reason` (str) and `evidence_ticket_ids` (list of str).
2. THE Schemas_Module SHALL treat all eight BriefItem fields as required.
3. IF a BriefItem receives a `rank` below 1, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a BriefItem receives a Blank_String for `cell_id` or `reason`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. IF a BriefItem receives a `lat` outside the inclusive range -90.0 to 90.0 or a `lon` outside the inclusive range -180.0 to 180.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. IF a BriefItem receives a `lat`, `lon` or `priority_score` that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
7. IF a BriefItem receives an empty `factors` list, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
8. IF a BriefItem receives a `priority_score` whose absolute difference from the Factor_Sum is greater than 1e-6, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
9. WHEN a BriefItem receives a `priority_score` whose absolute difference from the Factor_Sum is less than or equal to 1e-6, THE Schemas_Module SHALL accept the BriefItem.
10. IF a BriefItem receives an empty `evidence_ticket_ids` list or an `evidence_ticket_ids` list containing a Blank_String, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
11. THE Schemas_Module SHALL preserve the input order of `factors` and `evidence_ticket_ids` in a BriefItem.

### Requirement 7: BriefResponse model

**User Story:** As a crew supervisor, I want a pre-storm brief sized to my crews, so that the list matches what crews can visit.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a BriefResponse Model with the fields `date` (date), `forecast_rain_in` (float), `high_tide_flag` (bool), `crews` (int), `capacity_per_crew` (int, default 30), `items` (list of BriefItem) and `fallback_mode` (bool).
2. THE Schemas_Module SHALL treat every BriefResponse field except `capacity_per_crew` as required.
3. IF a BriefResponse receives a `forecast_rain_in` below 0.0 or equal to a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a BriefResponse receives a `crews` or `capacity_per_crew` value below 1, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. WHEN a BriefResponse receives an empty `items` list, THE Schemas_Module SHALL accept the BriefResponse.
6. IF a BriefResponse receives an `items` list longer than `crews` multiplied by `capacity_per_crew`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
7. WHEN a BriefResponse receives an `items` list whose length equals `crews` multiplied by `capacity_per_crew`, THE Schemas_Module SHALL accept the BriefResponse.
8. IF the `rank` values of a BriefResponse `items` list, read in list order, differ from the sequence 1, 2, ..., n where n is the list length, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.

### Requirement 8: BacklogItem model

**User Story:** As a 311 staff member, I want a prioritized backlog of open reports with honest status labels, so that I can see which cases need action.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a BacklogItem Model with the fields `ticket_id` (str), `cell_id` (str), `opened_at` (Aware_Datetime), `age_days` (float), `cause_label` (CauseLabel), `note_blank` (bool), `status_label` (str), `priority_score` (float), `factors` (list of FactorContribution) and `evidence_ticket_ids` (list of str).
2. THE Schemas_Module SHALL treat every BacklogItem field as required.
3. THE Schemas_Module SHALL define a module constant `STATUS_UNCLEAR` equal to the string `Status unclear`.
4. IF a BacklogItem receives a Blank_String for `ticket_id`, `cell_id` or `status_label`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. IF a BacklogItem receives an `opened_at` value without timezone information, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. IF a BacklogItem receives an `age_days` below 0.0 or an `age_days` or `priority_score` that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
7. IF a BacklogItem receives an empty `factors` list, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
8. IF a BacklogItem receives a `priority_score` whose absolute difference from the Factor_Sum is greater than 1e-6, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
9. IF a BacklogItem receives an empty `evidence_ticket_ids` list or an `evidence_ticket_ids` list containing a Blank_String, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
10. IF a BacklogItem has `note_blank` equal to True and a `status_label` other than exactly `STATUS_UNCLEAR`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
11. WHEN a BacklogItem has `note_blank` equal to True and `status_label` equal to `STATUS_UNCLEAR`, THE Schemas_Module SHALL accept the BacklogItem.
12. IF a BacklogItem is missing a required field or receives an invalid `cause_label` value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.

### Requirement 9: BacktestResult model

**User Story:** As a model developer, I want backtest results to include both baselines, so that results are reported honestly against random and most-past-complaints rankings.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a BacktestResult Model with exactly nine required fields: `storm_day` (date), `n_fixable_reports` (int), `n_cells` (int), and the six hit-rate fields `hit_rate_top100`, `hit_rate_top200`, `random_top100`, `random_top200`, `most_complaints_top100` and `most_complaints_top200`, each typed as a Rate.
2. IF a BacktestResult receives an `n_fixable_reports` below 0 or an `n_cells` below 1, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a BacktestResult receives any hit-rate field value outside the inclusive range 0.0 to 1.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a BacktestResult receives a top-100 value strictly greater than the matching top-200 value for the same ranking method, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the ranking method.
5. IF a BacktestResult receives a hit-rate field value that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. WHEN a BacktestResult receives a top-100 value equal to the matching top-200 value, THE Schemas_Module SHALL accept the BacktestResult.
7. WHEN a BacktestResult receives hit-rate field values of exactly 0.0 or exactly 1.0, THE Schemas_Module SHALL accept the BacktestResult.
8. WHEN a BacktestResult receives an `n_fixable_reports` of 0, THE Schemas_Module SHALL accept the BacktestResult.

### Requirement 10: RainTrendPoint model

**User Story:** As a city manager, I want a yearly count of heavy-rain days, so that the trend in storm frequency is visible.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a RainTrendPoint Model with the fields `year` (int) and `heavy_rain_days` (int).
2. THE Schemas_Module SHALL treat every RainTrendPoint field as required.
3. IF a RainTrendPoint receives a `year` outside the inclusive range 1900 to 2100, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a RainTrendPoint receives a `heavy_rain_days` outside the inclusive range 0 to 366, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. WHEN a RainTrendPoint receives a `year` of exactly 1900 or 2100 or a `heavy_rain_days` of exactly 0 or 366, THE Schemas_Module SHALL accept the RainTrendPoint.

### Requirement 11: Model serialization

**User Story:** As a module developer, I want models to serialize to snake_case JSON and back without loss, so that data crosses the HTTP boundary unchanged.

#### Acceptance Criteria

1. THE Schemas_Module SHALL serialize every Model to JSON with keys exactly matching the snake_case field names listed in Requirements 2 to 10, with no aliases and no extra keys.
2. THE Schemas_Module SHALL serialize enum fields as their string values, date fields as `YYYY-MM-DD` strings and datetime fields as ISO 8601 date-time strings.
3. FOR ALL valid instances of each Model, serializing with `model_dump_json` then validating with `model_validate_json` SHALL produce an instance equal (`==`) to the original (round-trip property).
4. IF a Model, including a nested Model, receives a field name not listed in the Model definition, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. WHEN an optional field holds None, THE Schemas_Module SHALL serialize the field key with a JSON `null` value.
6. IF `model_validate_json` receives an invalid enum string, an invalid date or datetime string, or syntactically invalid JSON, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.

### Requirement 12: Data path constants

**User Story:** As a module developer, I want shared path constants, so that no module hard-codes a data location.

#### Acceptance Criteria

1. THE Paths_Module SHALL define a `PROJECT_ROOT` constant as an absolute, symlink-resolved `pathlib.Path` equal to the parent of the `contracts/` directory, computed from the location of the Paths_Module file.
2. THE Paths_Module SHALL define `pathlib.Path` constants `REPORTS_PATH`, `CELLS_PATH`, `STORMS_PATH` and `DUPLICATE_PAIRS_PATH` pointing to `data/processed/reports.parquet`, `data/processed/cells.parquet`, `data/processed/storms.parquet` and `data/processed/duplicate_pairs.parquet` under the Project_Root.
3. THE Paths_Module SHALL define `pathlib.Path` constants `RAW_DIR`, `PROCESSED_DIR` and `DEMO_DIR` pointing to `data/raw/`, `data/processed/` and `data/demo/` under the Project_Root.
4. THE Paths_Module SHALL define a `FIXTURES_DIR` constant as a `pathlib.Path` pointing to `contracts/fixtures/` under the Project_Root.
5. WHEN the Paths_Module is imported, THE Paths_Module SHALL compute the constants without creating, reading or modifying any file or directory.
6. WHEN the Paths_Module is imported from any current working directory, THE Paths_Module SHALL produce the same `PROJECT_ROOT` value.
7. THE Paths_Module SHALL define `REPORTS_PATH`, `CELLS_PATH`, `STORMS_PATH`, `DUPLICATE_PAIRS_PATH`, `BASINS_PATH`, `FLOOD_AREAS_PATH` and `RAIN_TREND_PATH` so that the parent of each constant equals `PROCESSED_DIR`.
8. WHILE the files and directories referenced by the constants do not exist, THE Paths_Module SHALL import without error.
9. THE Paths_Module SHALL define `pathlib.Path` constants `BASINS_PATH`, `FLOOD_AREAS_PATH` and `RAIN_TREND_PATH` pointing to `data/processed/basins.parquet`, `data/processed/flood_areas.parquet` and `data/processed/rain_trend.parquet` under the Project_Root.

### Requirement 13: OpenAPI document

**User Story:** As a backend and frontend developer, I want one OpenAPI 3.1 document, so that the API and the web client agree on endpoints and payloads.

#### Acceptance Criteria

1. THE OpenAPI_Document SHALL declare `openapi: 3.1.0` and pass validation by an OpenAPI 3.1 validator.
2. THE OpenAPI_Document SHALL define a component schema for each Model and enum in the Schemas_Module, using the same names, field names, types, required fields and exactly the same sets of allowed enum values.
3. THE OpenAPI_Document SHALL define a `HealthResponse` component schema with required fields `status` (string) and `fallback` (boolean).
4. THE OpenAPI_Document SHALL define an `ErrorResponse` component schema with a required `detail` string field.
5. THE OpenAPI_Document SHALL represent date fields and parameters as `type: string` with `format: date`, and datetime fields as `type: string` with `format: date-time`.
6. THE OpenAPI_Document SHALL define `GET /health` with no parameters, returning a HealthResponse.
7. THE OpenAPI_Document SHALL define `GET /brief` with query parameters `date` (date, required), `crews` (integer, minimum 1, required) and `capacity_per_crew` (integer, minimum 1, default 30, optional), returning a BriefResponse.
8. THE OpenAPI_Document SHALL define `GET /backlog` with query parameter `limit` (integer, minimum 1, optional), returning an array of BacklogItem.
9. THE OpenAPI_Document SHALL define `GET /cells/{cell_id}/history` with required path parameter `cell_id` (string), returning an array of Report.
10. THE OpenAPI_Document SHALL define `GET /backtest` with no parameters, returning an array of BacktestResult.
11. THE OpenAPI_Document SHALL define `GET /rain-trend` with no parameters, returning an array of RainTrendPoint.
12. THE OpenAPI_Document SHALL reference ErrorResponse for the 404 response of `GET /cells/{cell_id}/history`.
13. THE OpenAPI_Document SHALL reference ErrorResponse for the 422 response of `GET /brief`, `GET /backlog` and `GET /cells/{cell_id}/history`.
14. THE OpenAPI_Document SHALL declare, for each of the 6 operations, a 200 response with `application/json` content whose schema is a `$ref` to a component schema or an array whose items are a `$ref` to a component schema.
15. THE OpenAPI_Document SHALL define exactly the 6 operations listed in criteria 6 to 11 and no other operations.
16. THE OpenAPI_Document SHALL contain only `$ref` values that resolve to a schema defined under `components.schemas`.

### Requirement 14: Fixtures

**User Story:** As a frontend developer, I want realistic fixture data, so that the app and tests run offline when the API is unreachable.

#### Acceptance Criteria

1. THE Fixture_Set SHALL contain exactly 9 JSON files named `report.json`, `cell.json`, `storm.json`, `factor_contribution.json`, `brief_item.json`, `brief_response.json`, `backlog_item.json`, `backtest_result.json` and `rain_trend_point.json`, one per Model, with no files for removed Models.
2. THE Fixture_Set SHALL store each file as a JSON array containing 3 to 5 instances of the matching Model.
3. THE Fixture_Set SHALL use Boston neighborhood names and coordinates within latitude 42.22 to 42.40 and longitude -71.20 to -70.98.
4. THE Fixture_Set SHALL use ticket IDs, cell IDs and storm days that are consistent across files, so that every `evidence_ticket_ids` value, every BacklogItem `ticket_id` and every non-null `duplicate_of` value references a ticket in `report.json`, every `cell_id` references a cell in `cell.json`, and every non-null Report `storm_day` and every BacktestResult `storm_day` references a storm in `storm.json`.
5. THE Fixture_Set SHALL include at least one Report with each CauseLabel value, at least one open Report, and at least one Report with a non-null `duplicate_of`.
6. THE Fixture_Set SHALL contain only synthetic example data, with no real resident names, phone numbers or email addresses.
7. THE Fixture_Set SHALL use unique `ticket_id` values within `report.json`, unique `cell_id` values within `cell.json`, unique `storm_day` values within `storm.json` and unique `year` values within `rain_trend_point.json`.
8. THE Fixture_Set SHALL use at least 3 distinct real Boston neighborhood names.
9. THE Fixture_Set SHALL set every non-null `duplicate_of` value to the `ticket_id` of a different Report in `report.json`.
10. THE Fixture_Set SHALL include at least one Report with `note_blank` equal to true.
11. THE Fixture_Set SHALL include at least one BacklogItem with `note_blank` equal to true and `status_label` equal to `Status unclear`.

### Requirement 15: Contract tests

**User Story:** As the team, I want automated contract tests, so that any change that breaks a contract fails `make test`.

#### Acceptance Criteria

1. THE Contract_Tests SHALL verify that every instance in every Fixture_Set file validates against its matching Model.
2. THE Contract_Tests SHALL verify that the Fixture_Set has a file for every Model and that each file contains 3 to 5 instances.
3. THE Contract_Tests SHALL verify that BriefItem raises a Pydantic ValidationError when `evidence_ticket_ids` is an empty list.
4. THE Contract_Tests SHALL verify that BacklogItem raises a Pydantic ValidationError when `evidence_ticket_ids` is an empty list.
5. THE Contract_Tests SHALL verify that a BacklogItem with `note_blank` equal to True and a `status_label` other than `Status unclear` raises a Pydantic ValidationError.
6. THE Contract_Tests SHALL verify that a BriefResponse with more `items` than `crews` multiplied by `capacity_per_crew` raises a Pydantic ValidationError.
7. THE Contract_Tests SHALL verify that the OpenAPI_Document is a valid OpenAPI 3.1 document.
8. THE Contract_Tests SHALL verify that every `$ref` in the OpenAPI_Document resolves to a schema defined under `components.schemas`.
9. THE Contract_Tests SHALL verify that every Model and enum name in the Schemas_Module has a matching component schema in the OpenAPI_Document.
10. THE Contract_Tests SHALL verify, using at least 100 Hypothesis-generated examples, that BriefItem and BacklogItem accept an `evidence_ticket_ids` list if and only if the list is non-empty and contains no Blank_String.
11. THE Contract_Tests SHALL verify, using at least 100 Hypothesis-generated examples, that a BacklogItem with `note_blank` equal to True is accepted if and only if `status_label` equals `Status unclear`.
12. THE Contract_Tests SHALL verify the round-trip property of Requirement 11 using at least 100 Hypothesis-generated examples per Model.
13. THE Contract_Tests SHALL verify the cross-file references of Requirement 14.4.
14. THE Contract_Tests SHALL run offline with `DRAINFAST_FALLBACK=1` and complete without network access.
15. IF a fixture instance fails validation, THEN THE Contract_Tests SHALL report a failure message naming the fixture file and the instance index.
16. IF any Contract_Tests check fails, THEN THE Contract_Tests SHALL cause `make test` to exit with a non-zero status.

### Requirement 16: Scope and dependencies

**User Story:** As the team lead, I want the contracts kept small and self-contained, so that every module can depend on them safely.

#### Acceptance Criteria

1. THE Contracts_Package SHALL limit created and modified files to the `contracts/` and `tests/contracts/` directories.
2. THE Contracts_Package SHALL import only the Python standard library and Pydantic v2 at runtime from files in `contracts/`.
3. THE Contracts_Package SHALL list every runtime and test dependency in `contracts/requirements.txt`, each pinned with `==`.
4. THE Contract_Tests SHALL import only the Python standard library, Pydantic v2, the Contracts_Package, pytest, hypothesis, PyYAML and openapi-spec-validator.
5. THE Contracts_Package SHALL list in `contracts/requirements.txt` only packages imported by files in `contracts/` or `tests/contracts/`.
6. THE Contracts_Package SHALL contain no imports, including function-local imports, from data_pipeline, model, evaluation, backend, mcp_server or frontend.
