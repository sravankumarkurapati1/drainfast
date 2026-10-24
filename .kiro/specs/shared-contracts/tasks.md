# Implementation Plan: shared-contracts

## Overview

Build the frozen DrainFast contracts in Python with Pydantic v2: package skeleton, `schemas.py`, `paths.py`, a hand-written `openapi.yaml`, 10 cross-consistent fixture files, then the pytest + Hypothesis contract tests in `tests/contracts/`. Only files in `contracts/` and `tests/contracts/` are created.

## Tasks

- [ ] 1. Set up contracts package skeleton
  - [ ] 1.1 Create package files, pinned dependencies and test config
    - Create empty `contracts/__init__.py` (no re-exports, no side effects)
    - Create `contracts/requirements.txt` pinning `pydantic==2.9.2`, `pytest==8.3.3`, `hypothesis==6.112.1`, `PyYAML==6.0.2`, `openapi-spec-validator==0.7.1`
    - Create `tests/contracts/__init__.py` and `tests/contracts/conftest.py`: insert project root into `sys.path`, set `DRAINFAST_FALLBACK=1`, autouse fixture patching `socket.socket.connect` to raise
    - _Requirements: 15.9, 16.1, 16.3, 16.5_

- [ ] 2. Implement contracts/schemas.py
  - [ ] 2.1 Define enums, ContractModel base and shared annotated types
    - `CauseLabel`, `LabelSource`, `ReportStatus`, `WorkOrderStatus`, `Priority`, `GridOrBasin` as `str` enums
    - `ContractModel` with `ConfigDict(extra="forbid")`
    - `NonBlankStr` (rejects blank, returns value unchanged), `Latitude`, `Longitude`, `Rate`, `RainInches`, `NonNegFloat` (all `allow_inf_nan=False`), `TicketIdList` (`min_length=1`)
    - Import only stdlib and pydantic
    - _Requirements: 1.1-1.11, 11.4, 16.2, 16.6_

  - [ ] 2.2 Implement Report, Location, Storm, BriefItem and WorkOrder models
    - Fields, defaults and `AwareDatetime` per design Data Models
    - Report validators: `closed_at >= opened_at`, open status implies `closed_at is None`, `duplicate_of != ticket_id`
    - Storm validator: `max_hourly_in <= rain_total_in`
    - WorkOrder `status` default `pending_approval`
    - _Requirements: 2.1-2.11, 3.1-3.7, 4.1-4.7, 5.1-5.9, 6.1-6.7_

  - [ ] 2.3 Implement StormSummary, BacktestResult, NeighborhoodEquity, CopilotRequest, CopilotResponse and registries
    - StormSummary validators: key set equals `set(CauseLabel)`, sum equals `report_count`, `duplicates_merged <= report_count`, unique `repeat_location_ids`
    - BacktestResult validator: per method `top100 <= top200`, message names the method
    - NeighborhoodEquity validators: `open_cases <= total_reports`, median None when `open_cases == total_reports`; `neighborhood` length 1-100
    - CopilotRequest `message` 1-2000 chars non-blank; CopilotResponse `tools_used` default empty, max 20
    - Define `ALL_MODELS` and `ALL_ENUMS` tuples
    - _Requirements: 7.1-7.9, 8.1-8.6, 9.1-9.5, 10.1-10.5, 11.1, 11.2, 11.5_

- [ ] 3. Implement contracts/paths.py
  - [ ] 3.1 Define path constants
    - `PROJECT_ROOT = Path(__file__).resolve().parent.parent`; `RAW_DIR`, `PROCESSED_DIR`, `DEMO_DIR`, `REPORTS_PATH`, `LOCATIONS_PATH`, `STORMS_PATH`, `DUPLICATE_PAIRS_PATH`, `FIXTURES_DIR`
    - Import only `pathlib`; no filesystem access
    - _Requirements: 12.1-12.8, 16.2_

- [ ] 4. Write contracts/openapi.yaml
  - [ ] 4.1 Author the OpenAPI 3.1.0 document
    - `components.schemas` for all 10 models, 6 enums and `ErrorResponse`; `additionalProperties: false`, 3.1-style nullable types, `format: date` / `date-time`, numeric bounds mirroring Pydantic
    - Exactly the 9 operations with parameters, `operationId`s, 200 `$ref` responses and 404/422 `ErrorResponse` refs per the design table
    - _Requirements: 13.1-13.17_

- [ ] 5. Create contracts/fixtures/
  - [ ] 5.1 Write location.json, storm.json and report.json
    - 3-5 synthetic instances each, Boston coordinates (lat 42.22-42.40, lon -71.20 to -70.98), at least 3 real neighborhood names
    - Unique ids/storm days; reports cover every CauseLabel, include an open report and a `duplicate_of` pointing at a different report; all `location_id` and `storm_day` values resolve
    - No real names, phone numbers or emails
    - _Requirements: 14.1-14.9_

  - [ ] 5.2 Write the remaining 7 fixture files
    - `brief_item.json`, `work_order.json`, `storm_summary.json`, `backtest_result.json`, `neighborhood_equity.json`, `copilot_request.json`, `copilot_response.json` in `model_dump(mode="json")` form
    - Every ticket, location and storm reference resolves to the files from 5.1
    - _Requirements: 14.1, 14.2, 14.4, 14.6_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Write contract tests in tests/contracts/
  - [ ] 7.1 Create strategies.py with Hypothesis builders
    - One `valid_<model>()` strategy per model satisfying cross-field rules (e.g. `closed_at = opened_at + timedelta`, `report_count = sum(counts_by_cause)`), aware datetimes with varied offsets
    - _Requirements: 15.7_

  - [ ] 7.2 Write test_fixtures.py
    - Define `FIXTURE_FILES` mapping; check all 10 files exist, 3-5 instances each, each validates with failure message `"{file}[{index}]: {error}"`
    - Check uniqueness, cross-file references, CauseLabel coverage, open report, duplicate, Boston bounds, >= 3 neighborhoods, no email/phone patterns
    - _Requirements: 14.1-14.9, 15.1, 15.2, 15.8, 15.10, 15.11_

  - [ ] 7.3 Write test_schemas.py unit tests
    - Enum value sets, required fields, defaults, boundary values (0.0, 1.0, equal timestamps, equal top100/top200, empty repeat list)
    - BriefItem with empty `evidence_ticket_ids` raises ValidationError; WorkOrder without `status` is `pending_approval`
    - Malformed JSON raises `json_invalid`
    - _Requirements: 1.1-1.6, 5.2, 6.2, 11.6, 15.3, 15.4_

  - [ ] 7.4 Write test_openapi.py
    - Validate with `openapi_spec_validator`; component names cover `ALL_MODELS` and `ALL_ENUMS`
    - Per model, compare property names, required set, enum values and type/format to `model_json_schema()`
    - Exactly 9 operations with listed params, 200 `$ref`s and 404/422 `ErrorResponse` refs
    - _Requirements: 13.1-13.17, 15.5, 15.6_

  - [ ] 7.5 Write test_paths.py
    - Constants are absolute `Path`s at expected locations; parquet paths have parent `PROCESSED_DIR`
    - Import via `subprocess` from a temp cwd yields the same `PROJECT_ROOT`; import creates no directories
    - _Requirements: 12.1-12.8_

  - [ ] 7.6 Write test_dependencies.py
    - AST scan (including function-local imports) of every `.py` in `contracts/` and `tests/contracts/` against allowed modules; no project-module imports
    - Every `requirements.txt` line pinned with `==` and every listed package imported
    - _Requirements: 16.2-16.6_

- [ ] 8. Write property-based tests in tests/contracts/test_roundtrip.py
  - [ ]* 8.1 Write property test for serialization round trip
    - **Property 1: Serialization round trip**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.5, 15.7**

  - [ ]* 8.2 Write property test for enum field validation
    - **Property 2: Enum fields accept exactly the enum values**
    - **Validates: Requirements 1.7, 1.8, 1.9, 1.10, 1.11**

  - [ ]* 8.3 Write property test for unknown field rejection
    - **Property 3: Unknown field names are rejected**
    - **Validates: Requirements 11.4**

  - [ ]* 8.4 Write property test for blank string rejection
    - **Property 4: Blank strings rejected in NonBlankStr fields and TicketIdList**
    - **Validates: Requirements 2.10, 3.7, 5.2, 5.5, 6.3, 6.4, 6.6, 7.9, 9.4, 10.2**

  - [ ]* 8.5 Write property test for float bounds
    - **Property 5: Non-finite and out-of-range floats rejected, inclusive bounds accepted**
    - **Validates: Requirements 2.4, 2.8, 3.2, 3.3, 3.5, 3.6, 4.2, 5.4, 5.7, 5.8, 8.2, 8.4, 8.6**

  - [ ]* 8.6 Write property test for Report consistency
    - **Property 6: Report consistency rules**
    - **Validates: Requirements 2.2, 2.3, 2.5, 2.7, 2.9**

  - [ ]* 8.7 Write property test for Storm rainfall ordering
    - **Property 7: max_hourly_in <= rain_total_in accepted iff holds**
    - **Validates: Requirements 4.3, 4.5**

  - [ ]* 8.8 Write property test for StormSummary rules
    - **Property 8: StormSummary key set, sum, duplicates and uniqueness**
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.6, 7.7, 7.8, 7.9**

  - [ ]* 8.9 Write property test for BacktestResult ordering
    - **Property 9: top100 <= top200 per method, error names the method**
    - **Validates: Requirements 8.3, 8.5**

  - [ ]* 8.10 Write property test for NeighborhoodEquity rules
    - **Property 10: open_cases <= total_reports, median None when no closed cases**
    - **Validates: Requirements 9.2, 9.3, 9.5**

  - [ ]* 8.11 Write property test for WorkOrder and BriefItem lists
    - **Property 11: WorkOrder default status and non-empty lists; BriefItem evidence non-empty and order preserved**
    - **Validates: Requirements 5.2, 5.9, 6.2, 6.3, 6.4**

- [ ] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each property test uses `@settings(max_examples=100)` or more and the tag comment `# Feature: shared-contracts, Property N: <title>`
- Root `requirements.txt` and `Makefile` changes are requested from owner C, not made here
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
    { "id": 5, "tasks": ["8.1"] },
    { "id": 6, "tasks": ["8.2"] },
    { "id": 7, "tasks": ["8.3"] },
    { "id": 8, "tasks": ["8.4"] },
    { "id": 9, "tasks": ["8.5"] },
    { "id": 10, "tasks": ["8.6"] },
    { "id": 11, "tasks": ["8.7"] },
    { "id": 12, "tasks": ["8.8"] },
    { "id": 13, "tasks": ["8.9"] },
    { "id": 14, "tasks": ["8.10"] },
    { "id": 15, "tasks": ["8.11"] }
  ]
}
```
