# Design Document: 01b-cells-and-flags

## Overview

`data_pipeline/cells.py` reads three raw files and one A1 output, and writes two files.

```
boston_catch_basins.csv ─┐
reports.parquet ─────────┼─ build_cells ─> cells.parquet
ej_block_groups.geojson ─┤   (cell_center, owner groups, mode neighborhood, flags)
flood_extent.json ─ build_flood_area ─> flood_area.geojson
```

## Components

| Function | Responsibility |
|---|---|
| `owner_group(code)` | OWNER_CODE to BWSC, City or Private (other agencies count as Private). |
| `basin_owner_label(groups)` | Single group, Mixed or Unknown. |
| `build_cells(basins, reports, ej_area, flood_area)` | Pure: one row per cell with counts, owner, share, neighborhood and flags. |
| `rings_to_polygon(rings)` | Esri rings to a shapely geometry: shoelace sign picks outer vs hole; an STRtree finds each hole's smallest containing outer. |
| `build_flood_area(path)` | Read the web-map export, check EPSG:3857, build, reproject to EPSG:4326, `make_valid`. |
| `write_flood_geojson(area, path)` | One-feature FeatureCollection, coordinates rounded to 1e-7 degrees. |
| `validate_cells(cells)` | Every row through `contracts.schemas.Cell`. |

## Decisions

- **Point-in-area uses the cell center**, as the plan specifies, so a cell's flags do
  not depend on which basins or reports it holds.
- **Other agencies count as Private.** The Cell contract has five owner values. DCR,
  MassDOT, Massport, MBTA, MWRA and neighboring towns are not BWSC's to clean, which is
  what the backend's `bwsc_share` factor needs. The raw codes stay in `owner_codes` for
  transparency.
- **Orphan holes** (holes no outer ring contains) are logged and ignored.
- **tree_density** is null in V1 (street trees are optional).

## Testing strategy

Hypothesis: `cell_id` is stable and its center maps back to it; every report's cell
exists, every basin and report is counted once, and every row is a valid Cell.
Unit tests: owner mapping, neighborhood mode, ring orientation with a hole and an island.
