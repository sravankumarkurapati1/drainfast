# Requirements Document

## Introduction

The shared contracts are the single source of truth for every data shape, file path and HTTP endpoint in DrainFast. They live in `contracts/` and are frozen: data_pipeline, model, evaluation, backend and frontend import or consume them and never redefine them. This spec covers the Pydantic v2 schemas (`contracts/schemas.py`), the data path constants (`contracts/paths.py`), the OpenAPI 3.1 document (`contracts/openapi.yaml`), JSON fixtures with realistic Boston examples (`contracts/fixtures/`), and the contract tests (`tests/contracts/`). Only files inside `contracts/` and `tests/contracts/` are created.

## Glossary

- **Contracts_Package**: The Python package at `contracts/` containing `schemas.py`, `paths.py`, `openapi.yaml` and `fixtures/`.
- **Schemas_Module**: The file `contracts/schemas.py` that defines all shared Pydantic v2 models and enums.
- **Paths_Module**: The file `contracts/paths.py` that defines all shared data file path constants.
- **OpenAPI_Document**: The file `contracts/openapi.yaml`, an OpenAPI 3.1 description of the DrainFast HTTP API.
- **Fixture_Set**: The JSON files in `contracts/fixtures/`, one file per model.
- **Contract_Tests**: The pytest test files in `tests/contracts/`.
- **Model**: Any Pydantic v2 class defined in the Schemas_Module (Report, Location, Storm, BriefItem, WorkOrder, StormSummary, BacktestResult, NeighborhoodEquity, CopilotRequest, CopilotResponse).
- **CauseLabel**: String enum with values `clogged_basin`, `grading_capacity`, `coastal_tide`, `unclear`.
- **LabelSource**: String enum with values `rule`, `llm`.
- **ReportStatus**: String enum with values `open`, `closed`.
- **WorkOrderStatus**: String enum with values `pending_approval`, `approved`, `rejected`.
- **Priority**: String enum with values `high`, `medium`, `low`.
- **GridOrBasin**: String enum with values `grid`, `basin`, describing whether a Location is a roughly 50 m grid cell or a catch basin point.
- **Evidence**: The list of past 311 ticket IDs a result is based on.
- **Storm_Day**: A calendar date (no time component) whose rainfall at Boston Logan meets the storm threshold.
- **Aware_Datetime**: A datetime carrying timezone information; DrainFast values are in America/New_York.
- **Rate**: A float in the closed range 0.0 to 1.0.
- **Project_Root**: The repository root directory `drainfast/`.
- **Blank_String**: A string that is empty or contains only whitespace characters.
- **Non_Finite_Float**: A float value that is NaN, positive infinity or negative infinity.

## Requirements

### Requirement 1: Cause and status enums

**User Story:** As a module developer, I want shared enums for cause labels and statuses, so that every module uses the same allowed values.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define CauseLabel as a `str` enum with exactly the values `clogged_basin`, `grading_capacity`, `coastal_tide` and `unclear` and no other values.
2. THE Schemas_Module SHALL define LabelSource as a `str` enum with exactly the values `rule` and `llm` and no other values.
3. THE Schemas_Module SHALL define ReportStatus as a `str` enum with exactly the values `open` and `closed` and no other values.
4. THE Schemas_Module SHALL define WorkOrderStatus as a `str` enum with exactly the values `pending_approval`, `approved` and `rejected` and no other values.
5. THE Schemas_Module SHALL define Priority as a `str` enum with exactly the values `high`, `medium` and `low` and no other values.
6. THE Schemas_Module SHALL define GridOrBasin as a `str` enum with exactly the values `grid` and `basin` and no other values.
7. IF a Model field typed with an enum receives a value outside that enum, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.
8. WHEN a Model field typed with an enum receives a string, THE Schemas_Module SHALL accept the string only if the string matches an enum value exactly, including letter case.
9. IF a Model field typed with an enum receives an empty string, a differently-cased string or a non-string value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.
10. IF a non-optional Model field typed with an enum receives None, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.
11. THE Schemas_Module SHALL serialize every enum field as the plain string value of the enum member.

### Requirement 2: Report model

**User Story:** As a 311 triage developer, I want a single Report model, so that the pipeline, backend and frontend agree on what a flood report contains.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a Report Model with the fields `ticket_id` (str), `opened_at` (Aware_Datetime), `closed_at` (optional Aware_Datetime, default None), `status` (ReportStatus), `lat` (float), `lon` (float), `location_id` (str), `text` (str), `closing_note` (optional str, default None), `cause_label` (CauseLabel), `label_source` (LabelSource), `storm_day` (optional date, default None), `neighborhood` (str), `ej_flag` (bool) and `duplicate_of` (optional str, default None).
2. IF a Report receives an `opened_at` or `closed_at` value without timezone information, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a Report receives a `closed_at` value strictly earlier than its `opened_at` value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a Report receives a `lat` outside the inclusive range -90.0 to 90.0 or a `lon` outside the inclusive range -180.0 to 180.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. IF a Report receives a `duplicate_of` value equal to its own `ticket_id`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. THE Schemas_Module SHALL treat every Report field without a default as required.
7. WHEN a Report receives a `closed_at` value equal to its `opened_at` value, THE Schemas_Module SHALL accept the Report.
8. IF a Report receives a `lat` or `lon` that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
9. IF a Report has `status` equal to `open` and a `closed_at` value other than None, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
10. IF a Report receives a Blank_String for `ticket_id`, `location_id` or `neighborhood`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
11. IF a Report is missing a required field or receives an invalid enum value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.

### Requirement 3: Location model

**User Story:** As a model developer, I want a shared Location model, so that rankings and maps refer to the same places.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a Location Model with the fields `location_id` (str), `lat` (float), `lon` (float), `grid_or_basin` (GridOrBasin), `tree_density` (float), `coastal_flag` (bool), `ej_flag` (bool) and `neighborhood` (str).
2. IF a Location receives a `tree_density` value below 0.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a Location receives a `lat` outside the inclusive range -90.0 to 90.0 or a `lon` outside the inclusive range -180.0 to 180.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. THE Schemas_Module SHALL treat every Location field as required, with no default values.
5. IF a Location receives a `tree_density`, `lat` or `lon` that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. WHEN a Location receives a `tree_density` value of 0.0, THE Schemas_Module SHALL accept the Location.
7. IF a Location receives a Blank_String for `location_id` or `neighborhood`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.

### Requirement 4: Storm model

**User Story:** As a data developer, I want a shared Storm model, so that storm days are described the same way in every module.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a Storm Model with the fields `storm_day` (date), `rain_total_in` (float), `max_hourly_in` (float) and `high_tide_flag` (bool).
2. IF a Storm receives a `rain_total_in` or `max_hourly_in` value below 0.0, above 30.0 or equal to a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a Storm receives a `max_hourly_in` strictly greater than its `rain_total_in`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. THE Schemas_Module SHALL treat every Storm field as required.
5. WHEN a Storm receives a `max_hourly_in` equal to its `rain_total_in`, THE Schemas_Module SHALL accept the Storm.
6. WHEN a Storm receives a `storm_day` string in ISO calendar date format `YYYY-MM-DD`, THE Schemas_Module SHALL accept the value as a date.
7. IF a Storm receives a `storm_day` datetime with a non-zero time component, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.

### Requirement 5: BriefItem model with mandatory evidence

**User Story:** As a crew supervisor, I want every brief item to carry evidence, so that I can check why a location was recommended.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a BriefItem Model with the fields `rank` (int), `location_id` (str), `lat` (float), `lon` (float), `risk_score` (float), `reason` (str) and `evidence_ticket_ids` (list of str).
2. IF a BriefItem receives an empty `evidence_ticket_ids` list or an `evidence_ticket_ids` list containing a Blank_String, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a BriefItem receives a `rank` below 1, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a BriefItem receives a `risk_score` outside the inclusive range 0.0 to 1.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. IF a BriefItem receives a Blank_String for `reason`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
6. THE Schemas_Module SHALL treat all seven BriefItem fields as required.
7. WHEN a BriefItem receives a `risk_score` of exactly 0.0 or exactly 1.0, THE Schemas_Module SHALL accept the BriefItem.
8. IF a BriefItem receives a `lat` outside the inclusive range -90.0 to 90.0 or a `lon` outside the inclusive range -180.0 to 180.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
9. THE Schemas_Module SHALL preserve the input order of `evidence_ticket_ids` in a BriefItem.

### Requirement 6: WorkOrder model with human approval default

**User Story:** As a 311 staff member, I want new work orders to wait for my approval, so that nothing is sent to crews automatically.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a WorkOrder Model with the fields `work_order_id` (str), `ticket_ids` (list of str), `location_id` (str), `cause_label` (CauseLabel), `department` (str), `priority` (Priority), `history_summary` (str), `evidence_ticket_ids` (list of str) and `status` (WorkOrderStatus).
2. WHEN a WorkOrder is created without a `status` value, THE Schemas_Module SHALL set `status` to `pending_approval`.
3. IF a WorkOrder receives an empty `ticket_ids` list or a `ticket_ids` list containing a Blank_String, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a WorkOrder receives an empty `evidence_ticket_ids` list or an `evidence_ticket_ids` list containing a Blank_String, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. THE Schemas_Module SHALL treat every WorkOrder field except `status` as required.
6. IF a WorkOrder receives a Blank_String for `work_order_id`, `location_id` or `department`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
7. IF a WorkOrder receives an invalid `status`, `priority` or `cause_label` value, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the field.

### Requirement 7: StormSummary model

**User Story:** As a BWSC manager, I want a consistent storm summary, so that post-storm reports have the same structure every time.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a StormSummary Model with the fields `storm_day` (date), `report_count` (int), `counts_by_cause` (mapping from CauseLabel to int), `duplicates_merged` (int) and `repeat_location_ids` (list of str).
2. IF a StormSummary receives a negative `report_count`, a negative `duplicates_merged` or a negative value in `counts_by_cause`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a StormSummary receives `counts_by_cause` values whose sum differs from `report_count`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a StormSummary receives a `duplicates_merged` value strictly greater than `report_count`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. THE Schemas_Module SHALL treat every StormSummary field as required.
6. WHEN a StormSummary receives an empty `repeat_location_ids` list, THE Schemas_Module SHALL accept the StormSummary.
7. WHEN a StormSummary receives a `duplicates_merged` value equal to `report_count`, THE Schemas_Module SHALL accept the StormSummary.
8. IF a StormSummary receives a `counts_by_cause` mapping that is missing any CauseLabel key or contains a key outside CauseLabel, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
9. IF a StormSummary receives a `repeat_location_ids` list containing a Blank_String or a duplicate entry, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.

### Requirement 8: BacktestResult model

**User Story:** As a model developer, I want backtest results to include both baselines, so that results are reported honestly against random and most-past-complaints rankings.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a BacktestResult Model with exactly seven required fields: `storm_day` (date), `hit_rate_top100`, `hit_rate_top200`, `random_top100`, `random_top200`, `most_complaints_top100` and `most_complaints_top200`, each hit-rate field typed as a Rate.
2. IF a BacktestResult receives any hit-rate field value outside the inclusive range 0.0 to 1.0, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a BacktestResult receives a top-100 value strictly greater than the matching top-200 value for the same ranking method, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError that names the ranking method.
4. IF a BacktestResult receives a hit-rate field value that is a Non_Finite_Float, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. WHEN a BacktestResult receives a top-100 value equal to the matching top-200 value, THE Schemas_Module SHALL accept the BacktestResult.
6. WHEN a BacktestResult receives hit-rate field values of exactly 0.0 or exactly 1.0, THE Schemas_Module SHALL accept the BacktestResult.

### Requirement 9: NeighborhoodEquity model

**User Story:** As a city manager, I want an equity view that counts open cases, so that under-served neighborhoods are visible.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a NeighborhoodEquity Model with the fields `neighborhood` (str), `total_reports` (int), `open_cases` (int), `median_hours_to_close` (optional float, default None) and `high_risk_low_reports` (bool).
2. IF a NeighborhoodEquity receives a negative `total_reports`, a negative `open_cases` or a negative `median_hours_to_close`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. IF a NeighborhoodEquity receives an `open_cases` value greater than `total_reports`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
4. IF a NeighborhoodEquity receives a `neighborhood` shorter than 1 character, longer than 100 characters or equal to a Blank_String, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. IF a NeighborhoodEquity receives a `median_hours_to_close` other than None while `open_cases` equals `total_reports`, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.

### Requirement 10: Co-pilot request and response models

**User Story:** As a frontend developer, I want fixed co-pilot message shapes, so that the chat panel works in both live and fallback mode.

#### Acceptance Criteria

1. THE Schemas_Module SHALL define a CopilotRequest Model with the field `message` (str).
2. IF a CopilotRequest receives a `message` shorter than 1 character, longer than 2000 characters or equal to a Blank_String, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
3. THE Schemas_Module SHALL define a CopilotResponse Model with the fields `answer` (str, required), `tools_used` (list of str, default empty list) and `fallback_mode` (bool, required, no default).
4. IF a CopilotResponse receives a `tools_used` list with more than 20 entries, THEN THE Schemas_Module SHALL raise a Pydantic ValidationError.
5. WHEN a CopilotResponse is serialized, THE Schemas_Module SHALL produce exactly the keys `answer`, `tools_used` and `fallback_mode`.

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
2. THE Paths_Module SHALL define `pathlib.Path` constants `REPORTS_PATH`, `LOCATIONS_PATH`, `STORMS_PATH` and `DUPLICATE_PAIRS_PATH` pointing to `data/processed/reports.parquet`, `data/processed/locations.parquet`, `data/processed/storms.parquet` and `data/processed/duplicate_pairs.parquet` under the Project_Root.
3. THE Paths_Module SHALL define `pathlib.Path` constants `RAW_DIR`, `PROCESSED_DIR` and `DEMO_DIR` pointing to `data/raw/`, `data/processed/` and `data/demo/` under the Project_Root.
4. THE Paths_Module SHALL define a `FIXTURES_DIR` constant as a `pathlib.Path` pointing to `contracts/fixtures/` under the Project_Root.
5. WHEN the Paths_Module is imported, THE Paths_Module SHALL compute the constants without creating, reading or modifying any file or directory.
6. WHEN the Paths_Module is imported from any current working directory, THE Paths_Module SHALL produce the same `PROJECT_ROOT` value.
7. THE Paths_Module SHALL define `REPORTS_PATH`, `LOCATIONS_PATH`, `STORMS_PATH` and `DUPLICATE_PAIRS_PATH` so that the parent of each constant equals `PROCESSED_DIR`.
8. WHILE the files and directories referenced by the constants do not exist, THE Paths_Module SHALL import without error.

### Requirement 13: OpenAPI document

**User Story:** As a backend and frontend developer, I want one OpenAPI 3.1 document, so that the API and the web client agree on endpoints and payloads.

#### Acceptance Criteria

1. THE OpenAPI_Document SHALL declare `openapi: 3.1.0` and pass validation by an OpenAPI 3.1 validator.
2. THE OpenAPI_Document SHALL define a component schema for each Model and enum in the Schemas_Module, using the same names, field names, types, required fields and exactly the same sets of allowed enum values.
3. THE OpenAPI_Document SHALL define `GET /brief` with query parameters `date` (date, required), `forecast_rain_in` (number, minimum 0, required) and `top_n` (integer, minimum 1, optional), returning an array of BriefItem.
4. THE OpenAPI_Document SHALL define `GET /queue` returning an array of Report.
5. THE OpenAPI_Document SHALL define `GET /locations/{location_id}/history` with path parameter `location_id` (string), returning an array of Report.
6. THE OpenAPI_Document SHALL define `GET /storms/{storm_day}/summary` with path parameter `storm_day` (date), returning a StormSummary.
7. THE OpenAPI_Document SHALL define `GET /backtest` returning an array of BacktestResult.
8. THE OpenAPI_Document SHALL define `GET /equity` returning an array of NeighborhoodEquity.
9. THE OpenAPI_Document SHALL define `POST /replay/{storm_day}` with path parameter `storm_day` (date), returning a StormSummary.
10. THE OpenAPI_Document SHALL define `POST /workorders/{work_order_id}/approve` with path parameter `work_order_id` (string), returning a WorkOrder.
11. THE OpenAPI_Document SHALL define `POST /copilot/chat` with a required CopilotRequest JSON request body, returning a CopilotResponse.
12. THE OpenAPI_Document SHALL define an `ErrorResponse` component schema with a required `detail` string field.
13. THE OpenAPI_Document SHALL represent date fields and parameters as `type: string` with `format: date`, and datetime fields as `type: string` with `format: date-time`.
14. THE OpenAPI_Document SHALL reference ErrorResponse for the 404 response of `GET /locations/{location_id}/history`, `GET /storms/{storm_day}/summary`, `POST /replay/{storm_day}` and `POST /workorders/{work_order_id}/approve`.
15. THE OpenAPI_Document SHALL reference ErrorResponse for the 422 response of `GET /locations/{location_id}/history`, `GET /storms/{storm_day}/summary`, `POST /replay/{storm_day}`, `POST /workorders/{work_order_id}/approve`, `GET /brief` and `POST /copilot/chat`.
16. THE OpenAPI_Document SHALL declare, for each of the 9 operations, a 200 response with `application/json` content whose schema is a `$ref` to a component schema or an array whose items are a `$ref` to a component schema.
17. THE OpenAPI_Document SHALL define exactly the 9 operations listed in criteria 3 to 11 and no other operations.

### Requirement 14: Fixtures

**User Story:** As a frontend developer, I want realistic fixture data, so that the app and tests run offline when the API is unreachable.

#### Acceptance Criteria

1. THE Fixture_Set SHALL contain exactly 10 JSON files named `report.json`, `location.json`, `storm.json`, `brief_item.json`, `work_order.json`, `storm_summary.json`, `backtest_result.json`, `neighborhood_equity.json`, `copilot_request.json` and `copilot_response.json`, one per Model.
2. THE Fixture_Set SHALL store each file as a JSON array containing 3 to 5 instances of the matching Model.
3. THE Fixture_Set SHALL use Boston neighborhood names and coordinates within latitude 42.22 to 42.40 and longitude -71.20 to -70.98.
4. THE Fixture_Set SHALL use ticket IDs, location IDs and storm days that are consistent across files, so that every `evidence_ticket_ids`, `ticket_ids` and `duplicate_of` value references a ticket in `report.json`, every `location_id` references a location in `location.json`, and every non-null `storm_day` references a storm in `storm.json`.
5. THE Fixture_Set SHALL include at least one Report with each CauseLabel value, at least one open Report, and at least one Report with a non-null `duplicate_of`.
6. THE Fixture_Set SHALL contain only synthetic example data, with no real resident names, phone numbers or email addresses.
7. THE Fixture_Set SHALL use unique `ticket_id` values within `report.json`, unique `location_id` values within `location.json` and unique `storm_day` values within `storm.json`.
8. THE Fixture_Set SHALL use at least 3 distinct real Boston neighborhood names.
9. THE Fixture_Set SHALL set every non-null `duplicate_of` value to the `ticket_id` of a different Report in `report.json`.

### Requirement 15: Contract tests

**User Story:** As the team, I want automated contract tests, so that any change that breaks a contract fails `make test`.

#### Acceptance Criteria

1. THE Contract_Tests SHALL verify that every instance in every Fixture_Set file validates against its matching Model.
2. THE Contract_Tests SHALL verify that the Fixture_Set has a file for every Model.
3. THE Contract_Tests SHALL verify that BriefItem raises a Pydantic ValidationError when `evidence_ticket_ids` is an empty list.
4. THE Contract_Tests SHALL verify that a WorkOrder created without `status` has `status` equal to `pending_approval`.
5. THE Contract_Tests SHALL verify that the OpenAPI_Document is a valid OpenAPI 3.1 document.
6. THE Contract_Tests SHALL verify that every Model and enum name in the Schemas_Module has a matching component schema in the OpenAPI_Document.
7. THE Contract_Tests SHALL verify the round-trip property of Requirement 11 using at least 100 Hypothesis-generated examples per Model.
8. THE Contract_Tests SHALL verify the cross-file references of Requirement 14.4.
9. THE Contract_Tests SHALL run offline with `DRAINFAST_FALLBACK=1` and complete without network access.
10. IF a fixture instance fails validation, THEN THE Contract_Tests SHALL report a failure message naming the fixture file and the instance index.
11. THE Contract_Tests SHALL verify that each Fixture_Set file contains 3 to 5 instances.
12. IF any Contract_Tests check fails, THEN THE Contract_Tests SHALL cause `make test` to exit with a non-zero status.

### Requirement 16: Scope and dependencies

**User Story:** As the team lead, I want the contracts kept small and self-contained, so that every module can depend on them safely.

#### Acceptance Criteria

1. THE Contracts_Package SHALL limit created and modified files to the `contracts/` and `tests/contracts/` directories.
2. THE Contracts_Package SHALL import only the Python standard library and Pydantic v2 at runtime from files in `contracts/`.
3. THE Contracts_Package SHALL list every runtime and test dependency in `contracts/requirements.txt`, each pinned with `==`.
4. THE Contract_Tests SHALL import only the Python standard library, Pydantic v2, the Contracts_Package, pytest, hypothesis, PyYAML and openapi-spec-validator.
5. THE Contracts_Package SHALL list in `contracts/requirements.txt` only packages imported by files in `contracts/` or `tests/contracts/`.
6. THE Contracts_Package SHALL contain no imports, including function-local imports, from data_pipeline, model, evaluation, backend, mcp_server or frontend.
