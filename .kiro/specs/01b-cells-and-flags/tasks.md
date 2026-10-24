# Implementation Plan: 01b-cells-and-flags

- [x] 1. Owner groups and cell builder in `data_pipeline/cells.py`
  - `owner_group`, `basin_owner_label`, `build_cells`
  - _Requirements: 1.1-1.4, 2.1-2.4, 3.1, 4.1_
- [x] 2. Flood area from the ArcGIS export
  - `rings_to_polygon`, `build_flood_area`, `write_flood_geojson`
  - _Requirements: 5.1-5.4_
- [x] 3. CLI `python -m data_pipeline.cells` with Cell validation and summary
  - _Requirements: 6.1, 6.2_
- [x] 4. Property tests in `tests/data_pipeline/test_cells.py`
  - [x] 4.1 Identical coordinates give the same cell_id (Property 1)
  - [x] 4.2 Every report's cell_id exists in cells (Property 2)
  - _Requirements: 7.1_
- [x] 5. Verify: `make cells`; flood area sits on Boston, not in the ocean
  - _Requirements: 5.5_
