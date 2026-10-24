# Implementation Plan: shared-contracts

## Overview

Build the frozen DrainFast V1 contracts in Python with Pydantic v2: package skeleton, `schemas.py` (9 models, 4 enums), `paths.py`, a hand-written `openapi.yaml` with 6 operations, 9 cross-consistent fixture files, then the pytest + Hypothesis contract tests in `tests/contracts/`. Only files in `contracts/` and `tests/contracts/` are created; no code exists yet, so every task is new.

## Tasks

- [ ] 1. Set up contracts package skeleton
  - [ ] 1.1 Create package files, pinned dependencies and test config
    - Create empty `contracts/__init__.py` (no re-exports, no side effects)
    - Create `contracts/requirements.txt` pinning `pydantic==2.9.2`, `pytest==8.3.3`, `hypothesis==6.112.1`, `PyYAML==6.0.2`, `openapi-spec-validator==0.7.1`
    - Create `tests/contracts/__init__.py` and `tests/contracts/conftest.py`: insert project root into `sys.path`, set `DRAINFAST_FALLBACK=1`, autouse fixture patching `socket.socket.connect` to raise
    - _Requirements: 15.14, 16.1, 16.3, 16.5_

- [ ] 2. Implement contracts/schemas.py
  - [ ] 2.1 Define enums, ContractModel base, annotated types, constants and helper
    - `CauseLabel`, `LabelSource`, `ReportStatus`, `BasinOwner` as `str` enums
    - `ContractModel` with `ConfigDict(extra="forbid")`
    - `NonBlankStr`, `Latitude`, `Longitude`, `Rate`, `RainInches`, `NonNegFloat`, `FiniteFloat` (all floats `allow_inf_nan=False`), `TicketIdList` (`min_length=1`, NonBlankStr items)
    - Constants `STORM_DAY_THRESHOLD_IN = 1.0`, `STATUS_UNCLEAR = "Status unclear"`, `FACTOR_SUM_TOLERANCE = 1e-6`; helper `_check_factor_sum(priority_score, factors)`
    - Import only stdlib and pydantic
    - _Requirements: 1.1-1.9, 4.8, 8.3, 11.4, 16.2, 16.6_

  - [ ] 2.2 Implement Report, Cell, Storm and FactorContribution models
    - Fields, defaults and `AwareDatetime` per design Data Models
    - Report validators: `closed_at >= opened_at`, open status implies `closed_at is None`, `duplicate_of != ticket_id`
    - Storm validator `max_hourly_in <= rain_total_in`; method `is_storm_day(threshold=STORM_DAY_THRESHOLD_IN)`
    - _Requirements: 2.1-2.11, 3.1-3.9, 4.1-4.11, 5.1-5.5_

  - [ ] 2.3 Implement BriefItem, BriefResponse, BacklogItem, BacktestResult, RainTrendPoint and registries
    - BriefItem / BacklogItem: non-empty `factors` with `_check_factor_sum`, non-empty `evidence_ticket_ids` preserving order
    - BacklogItem: `note_blank` true requires `status_label == STATUS_UNCLEAR`
    - BriefResponse: `capacity_per_crew` default 30, `len(items) <= crews * capacity_per_crew`, ranks equal `1..n`
    - BacktestResult: per method `top100 <= top200`, message names the method
    - RainTrendPoint: `1900 <= year <= 2100`, `0 <= heavy_rain_days <= 366`
    - Define `ALL_MODELS` (9 models) and `ALL_ENUMS` (4 enums) tuples
    - _Requirements: 6.1-6.11, 7.1-7.8, 8.1-8.12, 9.1-9.8, 10.1-10.5, 11.1-11.6_

- [ ] 3. Implement contracts/paths.py
  - [ ] 3.1 Define path constants
    - `PROJECT_ROOT = Path(__file__).resolve().parent.parent`, data dirs, processed parquet paths including `CELLS_PATH`, `BASINS_PATH`, `FLOOD_AREAS_PATH`, `RAIN_TREND_PATH`, and `FIXTURES_DIR`
    - Import only `pathlib`; no filesystem access at import
    - _Requirements: 12.1-12.9, 16.2_

- [ ] 4. Write contracts/openapi.yaml
  - [ ] 4.1 Author the OpenAPI 3.1.0 document
    - `components.schemas` for the 9 models, 4 enums, `HealthResponse` and `ErrorResponse`; `additionalProperties: false`, 3.1-style nullable types, `format: date` / `date-time`, numeric bounds mirroring Pydantic
    - Exactly 6 operations: `/health`, `/brief`, `/backlog`, `/cells/{cell_id}/history`, `/backtest`, `/rain-trend` with parameters, `operationId`s, 200 `$ref` responses and 404/422 `ErrorResponse` refs per the design table
    - Every `$ref` resolves under `components.schemas`
    - _Requirements: 13.1-13.16_

- [ ] 5. Create contracts/fixtures/
  - [x] 5.1 Write cell.json, storm.json and report.json
    - 3-5 synthetic instances each, Boston coordinates, at least 3 real neighborhood names
    - Unique ids/storm days; reports cover every CauseLabel, include a `note_blank` report, an open report and a `duplicate_of` pointing at a different report; all `cell_id` and storm day values resolve
    - No real names, phone numbers or emails
    - _Requirements: 14.1-14.10_

  - [ ] 5.2 Write the remaining 6 fixture files
    - `factor_contribution.json`, `brief_item.json`, `brief_response.json`, `backlog_item.json`, `backtest_result.json`, `rain_trend_point.json` in `model_dump(mode="json")` form
    - `backlog_item.json` includes a `note_blank` item with `status_label` "Status unclear"
    - Every ticket, cell and storm reference resolves to the files from 5.1; factor sums match `priority_score`
    - _Requirements: 14.1, 14.2, 14.4, 14.6, 14.11_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Write contract tests in tests/contracts/
  - [ ] 7.1 Create strategies.py with Hypothesis builders
    - One `valid_<model>()` strategy per model satisfying cross-field rules (`closed_at = opened_at + timedelta`, factor contributions summing to `priority_score`, ranks `1..n` within capacity, `STATUS_UNCLEAR` when `note_blank`), aware datetimes with varied offsets
    - _Requirements: 15.12_

  - [ ] 7.2 Write test_fixtures.py
    - Define `FIXTURE_FILES` mapping; all 9 files exist with 3-5 instances each, each validates with failure message `"{file}[{index}]: {error}"`
    - Uniqueness, cross-file references, CauseLabel coverage, open report, duplicate, `note_blank` Report, "Status unclear" BacklogItem, Boston bounds, >= 3 neighborhoods, no email/phone patterns
    - _Requirements: 14.1-14.11, 15.1, 15.2, 15.13, 15.15_

  - [ ] 7.3 Write test_schemas.py unit tests
    - Enum value sets, required fields, defaults (`capacity_per_crew == 30`), boundary values
    - `STORM_DAY_THRESHOLD_IN == 1.0` and `is_storm_day(1.0)` True at exactly 1.0
    - BriefItem and BacklogItem with empty `evidence_ticket_ids` raise ValidationError; BacklogItem `note_blank` without "Status unclear" raises; BriefResponse over capacity raises
    - _Requirements: 4.8, 4.10, 15.3, 15.4, 15.5, 15.6_

  - [ ] 7.4 Write test_openapi.py
    - Validate as OpenAPI 3.1 with `openapi_spec_validator`; every `$ref` resolves
    - Component names cover `ALL_MODELS`, `ALL_ENUMS`, `HealthResponse`, `ErrorResponse`
    - Per model, compare property names, required set, enum values and type/format to `model_json_schema()`
    - Exactly 6 operations with listed params, 200 `$ref`s and 404/422 `ErrorResponse` refs
    - _Requirements: 13.1-13.16, 15.7, 15.8, 15.9_

  - [ ] 7.5 Write test_paths.py
    - Constants are absolute `Path`s at expected locations incl. `CELLS_PATH`, `BASINS_PATH`, `FLOOD_AREAS_PATH`, `RAIN_TREND_PATH`; processed paths have parent `PROCESSED_DIR`
    - Import via `subprocess` from a temp cwd yields the same `PROJECT_ROOT`; import creates no directories
    - _Requirements: 12.1-12.9_

  - [ ] 7.6 Write test_dependencies.py
    - AST scan (including function-local imports) of every `.py` in `contracts/` and `tests/contracts/` against allowed modules; no project-module imports
    - Every `requirements.txt` line pinned with `==` and every listed package imported
    - _Requirements: 16.1-16.6_

- [ ] 8. Write property-based tests in tests/contracts/test_roundtrip.py
  - [ ]* 8.1 Write property test for serialization round trip
    - **Property 1: Serialization round trip**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.5, 15.12**

  - [ ]* 8.2 Write property test for enum field validation
    - **Property 2: Enum fields accept exactly enum values**
    - **Validates: Requirements 1.5, 1.6, 1.7, 1.8, 1.9**

  - [ ]* 8.3 Write property test for unknown field rejection
    - **Property 3: Unknown fields rejected**
    - **Validates: Requirements 11.4**

  - [ ]* 8.4 Write property test for blank string rejection
    - **Property 4: Blank strings rejected in NonBlankStr fields**
    - **Validates: Requirements 2.10, 3.3, 5.3, 6.4, 8.4**

  - [ ]* 8.5 Write property test for float bounds
    - **Property 5: Float bounds and finiteness**
    - **Validates: Requirements 2.4, 2.8, 3.4, 3.5, 3.7, 3.8, 4.2, 5.4, 6.5, 6.6, 8.6, 9.3, 9.5, 9.7**

  - [ ]* 8.6 Write property test for Report consistency
    - **Property 6: Report consistency**
    - **Validates: Requirements 2.2, 2.3, 2.5, 2.7, 2.9**

  - [ ]* 8.7 Write property test for Storm ordering and is_storm_day
    - **Property 7: Storm ordering and is_storm_day**
    - **Validates: Requirements 4.3, 4.5, 4.10, 4.11**

  - [ ] 8.8 Write property test for the evidence rule
    - **Property 8: Evidence rule**
    - **Validates: Requirements 6.10, 6.11, 8.9, 15.3, 15.4, 15.10**

  - [ ] 8.9 Write property test for the Status unclear rule
    - **Property 9: Status unclear rule**
    - **Validates: Requirements 8.10, 8.11, 15.5, 15.11**

  - [ ]* 8.10 Write property test for factor sum
    - **Property 10: Factor sum**
    - **Validates: Requirements 6.7, 6.8, 6.9, 8.7, 8.8**

  - [ ]* 8.11 Write property test for BriefResponse capacity and ranks
    - **Property 11: BriefResponse capacity and rank sequence**
    - **Validates: Requirements 7.6, 7.7, 7.8, 15.6**

  - [ ]* 8.12 Write property test for BacktestResult ordering
    - **Property 12: BacktestResult ordering**
    - **Validates: Requirements 9.4, 9.6**

  - [ ]* 8.13 Write property test for RainTrendPoint bounds
    - **Property 13: RainTrendPoint bounds**
    - **Validates: Requirements 10.3, 10.4, 10.5**

- [ ] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP; Properties 8 and 9 are required by explicit user request
- Each property test uses `@settings(max_examples=100)` or more and the tag comment `# Feature: shared-contracts, Property N: <title>`
- Root `requirements.txt` and `Makefile` changes are requested from their owner, not made here
- Property tests share `test_roundtrip.py`, so they run in separate waves

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1", "5.1"] },
    { "id": 2, "tasks": ["2.2", "5.2"] },
    { "id": 3, "tasks": ["2.3"] },
    { "id": 4, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6"] },
    { "id": 5, "tasks": ["8.8"] },
    { "id": 6, "tasks": ["8.9"] },
    { "id": 7, "tasks": ["8.1"] },
    { "id": 8, "tasks": ["8.2"] },
    { "id": 9, "tasks": ["8.3"] },
    { "id": 10, "tasks": ["8.4"] },
    { "id": 11, "tasks": ["8.5"] },
    { "id": 12, "tasks": ["8.6"] },
    { "id": 13, "tasks": ["8.7"] },
    { "id": 14, "tasks": ["8.10"] },
    { "id": 15, "tasks": ["8.11"] },
    { "id": 16, "tasks": ["8.12"] },
    { "id": 17, "tasks": ["8.13"] }
  ]
}
```
