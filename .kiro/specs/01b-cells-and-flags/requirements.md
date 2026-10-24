# Requirements Document: 01b-cells-and-flags

## Introduction

Member A's second spec. `python -m data_pipeline.cells` builds
`data/demo/cells.parquet` (one `contracts.schemas.Cell` per row, plus `bwsc_share`,
`owner_codes` and `report_count`) and `data/demo/flood_area.geojson`. It runs after
`make data`, because it reads `data/demo/reports.parquet`.

## Requirements

### Requirement 1: Cells

1. THE builder SHALL create one cell for every `contracts.cells.cell_id` that holds at
   least one catch basin from `data/raw/basins/boston_catch_basins.csv` (columns `lat`,
   `lon`, `OWNER_CODE`) or at least one report from `data/demo/reports.parquet`.
2. THE cell `lat` and `lon` SHALL be `contracts.cells.cell_center(cell_id)`. The grid
   SHALL never be redefined.
3. Identical coordinates SHALL always give the same `cell_id`.
4. Every report's `cell_id` SHALL exist in cells; the build SHALL fail otherwise.

### Requirement 2: Basins and owners

1. `basin_count` SHALL be the number of basins in the cell (0 when none).
2. Owner groups SHALL be: BWSC (BWSC); City (BPRD, BHA); Private (PRIV). Other agency
   codes (DCR, DOT, MPA, MTA, MHD, MBTA, MWRA, BRKLN, NEWTON, MILTON) SHALL be grouped
   with Private, because they are not BWSC's or the City's to clean.
3. `basin_owner` SHALL be the single group when all basins share one, Mixed when there
   is more than one group, and Unknown when the cell has no basins.
4. `bwsc_share` SHALL be BWSC basins divided by `basin_count`, and 0.0 when there are no
   basins. Depth fields SHALL be ignored.

### Requirement 3: Neighborhood

1. `neighborhood` SHALL be the most common non-Unknown neighborhood among the cell's
   reports, ties broken alphabetically, and "Unknown" when there is none.

### Requirement 4: EJ flag

1. `ej_flag` SHALL be true when the cell center lies inside any polygon of
   `data/raw/ej/ej_block_groups_boston.geojson` (lon/lat; every polygon is an EJ area).

### Requirement 5: Flood area

1. THE builder SHALL read rings from `layers[0].featureSet.features[0].geometry.rings` in
   `data/raw/flood/stormwater_flood_extent_near_9in.json` (EPSG:3857).
2. Clockwise rings SHALL be outer boundaries and counter-clockwise rings holes; each hole
   SHALL belong to the smallest outer ring containing it.
3. THE polygon SHALL be reprojected to EPSG:4326 with pyproj, fixed with shapely
   `make_valid`, and saved to `data/demo/flood_area.geojson`.
4. `flood_area_flag` SHALL be true when the cell center lies inside the flood area.
5. **Verify:** the flood area SHALL sit on Boston, not in the ocean.

### Requirement 6: Output and validation

1. Every row SHALL validate as `contracts.schemas.Cell` (extra columns checked separately).
2. THE builder SHALL print cell counts, owner counts, flag counts and flood-area bounds.

### Requirement 7: Property tests

1. Hypothesis tests SHALL check: identical coordinates give the same `cell_id`; every
   report's `cell_id` exists in cells.
