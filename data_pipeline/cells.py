"""Build data/demo/cells.parquet and data/demo/flood_area.geojson.

Usage:
    python -m data_pipeline.cells
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from pyproj import Transformer
from shapely import STRtree, make_valid
from shapely.geometry import Polygon, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from contracts.cells import cell_center, cell_id
from data_pipeline import paths
from data_pipeline.geo import load_polygons, points_in_area

log = logging.getLogger("data_pipeline.cells")

# OWNER_CODE -> owner group. The plan names BWSC, City (BPRD, BHA) and Private (PRIV).
# Other agencies (state, MBTA, Massport, neighboring towns) are not BWSC's or the City's
# to clean, so they are grouped with Private. Raise with C if the team wants another rule.
OWNER_GROUPS: dict[str, str] = {
    "BWSC": "BWSC",
    "BPRD": "City",
    "BHA": "City",
    "PRIV": "Private",
}
OTHER_OWNER_GROUP = "Private"

CELL_COLUMNS: tuple[str, ...] = (
    "cell_id", "lat", "lon", "neighborhood", "basin_count", "basin_owner",
    "ej_flag", "flood_area_flag", "tree_density",
)
EXTRA_COLUMNS: tuple[str, ...] = ("bwsc_share", "owner_codes", "report_count")

CELLS_SCHEMA = pa.schema([
    ("cell_id", pa.string()),
    ("lat", pa.float64()),
    ("lon", pa.float64()),
    ("neighborhood", pa.string()),
    ("basin_count", pa.int64()),
    ("basin_owner", pa.string()),
    ("ej_flag", pa.bool_()),
    ("flood_area_flag", pa.bool_()),
    ("tree_density", pa.float64()),
    ("bwsc_share", pa.float64()),
    ("owner_codes", pa.string()),
    ("report_count", pa.int64()),
])


# ---------------------------------------------------------------- flood area


def _signed_area(ring: np.ndarray) -> float:
    """Shoelace area: negative for clockwise rings (y axis pointing up)."""
    x, y = ring[:, 0], ring[:, 1]
    return 0.5 * float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


def rings_to_polygon(rings: list[list[list[float]]]) -> BaseGeometry:
    """Build one geometry from Esri JSON rings: clockwise = outer, counter-clockwise = hole.

    Each hole goes to the smallest outer ring that contains it. Degenerate rings are skipped.
    """
    outers: list[Polygon] = []
    holes: list[np.ndarray] = []
    for raw in rings:
        ring = np.asarray(raw, dtype=float)
        if len(ring) < 4:
            continue
        area = _signed_area(ring)
        if area < 0:
            outers.append(make_valid(Polygon(ring)))
        elif area > 0:
            holes.append(ring)
    if not outers:
        raise ValueError("flood area has no outer rings")

    shells = [o if isinstance(o, Polygon) else max(getattr(o, "geoms", [o]), key=lambda g: g.area)
              for o in outers]
    tree = STRtree(shells)
    hole_lists: list[list[np.ndarray]] = [[] for _ in shells]
    orphan = 0
    for ring in holes:
        point = Polygon(ring).representative_point()
        hits = [int(i) for i in tree.query(point, predicate="within")]
        if not hits:
            orphan += 1
            continue
        best = min(hits, key=lambda i: shells[i].area)
        hole_lists[best].append(ring)
    if orphan:
        log.info("flood area: %d holes outside every outer ring were ignored", orphan)

    parts = [
        make_valid(Polygon(shell.exterior.coords, [h for h in hole_lists[i]]))
        for i, shell in enumerate(shells)
    ]
    return make_valid(unary_union(parts))


def build_flood_area(path: Path) -> BaseGeometry:
    """Read the ArcGIS web-map export and return the flood area in EPSG:4326 (lon, lat)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    feature = data["layers"][0]["featureSet"]["features"][0]
    wkid = (feature["geometry"].get("spatialReference") or {}).get("latestWkid") or \
        (feature["geometry"].get("spatialReference") or {}).get("wkid") or 3857
    if int(wkid) not in (3857, 102100):
        raise ValueError(f"flood area: expected EPSG:3857, got wkid {wkid}")
    mercator = rings_to_polygon(feature["geometry"]["rings"])
    to_lonlat = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    def _reproject(coords: np.ndarray) -> np.ndarray:
        lon, lat = to_lonlat.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([lon, lat])

    area = make_valid(shapely.transform(mercator, _reproject))
    shapely.prepare(area)
    return area


def write_flood_geojson(area: BaseGeometry, path: Path) -> None:
    """Save the flood area as a one-feature GeoJSON FeatureCollection (lon, lat)."""
    shapely_area = shapely.set_precision(area, 1e-7)
    collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Climate Ready Boston stormwater flood extent (near 9 in)"},
            "geometry": mapping(shapely_area),
        }],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection), encoding="utf-8")


# ---------------------------------------------------------------- cells


def owner_group(code: object) -> str:
    """Map one OWNER_CODE to BWSC, City or Private."""
    key = str(code).strip().upper() if code is not None else ""
    return OWNER_GROUPS.get(key, OTHER_OWNER_GROUP)


def basin_owner_label(groups: set[str]) -> str:
    """Owner of a cell from the owner groups of its basins."""
    if not groups:
        return "Unknown"
    if len(groups) > 1:
        return "Mixed"
    return next(iter(groups))


def _mode_neighborhood(values: pd.Series) -> str:
    """Most common neighborhood; ties broken alphabetically; Unknown when none."""
    vals = values[values.fillna("").str.strip().ne("") & values.ne("Unknown")]
    if vals.empty:
        return "Unknown"
    counts = vals.value_counts()
    top = counts[counts == counts.max()].index
    return sorted(top)[0]


def build_cells(
    basins: pd.DataFrame,
    reports: pd.DataFrame,
    ej_area: BaseGeometry | None,
    flood_area: BaseGeometry | None,
) -> pd.DataFrame:
    """One row per cell that holds at least one basin or report.

    basins needs lat, lon, OWNER_CODE; reports needs cell_id and neighborhood.
    """
    b = basins.loc[:, ["lat", "lon", "OWNER_CODE"]].copy()
    b["lat"] = pd.to_numeric(b["lat"], errors="coerce")
    b["lon"] = pd.to_numeric(b["lon"], errors="coerce")
    bad = b["lat"].isna() | b["lon"].isna()
    if bad.any():
        log.info("basins: dropped %d rows with missing coordinates", int(bad.sum()))
    b = b.loc[~bad]
    b["cell_id"] = [cell_id(la, lo) for la, lo in zip(b["lat"], b["lon"])]
    b["code"] = b["OWNER_CODE"].fillna("").astype(str).str.strip().str.upper()
    b["group"] = b["code"].map(owner_group)

    basin_stats = b.groupby("cell_id").agg(
        basin_count=("cell_id", "size"),
        bwsc_count=("group", lambda g: int((g == "BWSC").sum())),
        groups=("group", lambda g: frozenset(g)),
        owner_codes=("code", lambda c: ",".join(sorted(set(c) - {""}))),
    )
    report_stats = reports.groupby("cell_id").agg(
        report_count=("cell_id", "size"),
        neighborhood=("neighborhood", _mode_neighborhood),
    )

    ids = sorted(set(basin_stats.index) | set(report_stats.index))
    cells = pd.DataFrame({"cell_id": ids})
    centers = [cell_center(c) for c in ids]
    cells["lat"] = [c[0] for c in centers]
    cells["lon"] = [c[1] for c in centers]
    cells = cells.join(basin_stats, on="cell_id").join(report_stats, on="cell_id")

    for col in ("basin_count", "bwsc_count", "report_count"):
        cells[col] = pd.to_numeric(cells[col], errors="coerce").fillna(0).astype("int64")
    cells["basin_owner"] = [basin_owner_label(set(g) if isinstance(g, frozenset) else set())
                            for g in cells["groups"]]
    cells["bwsc_share"] = np.where(cells["basin_count"] > 0,
                                   cells["bwsc_count"] / cells["basin_count"].clip(lower=1), 0.0)
    cells["owner_codes"] = cells["owner_codes"].fillna("")
    cells["neighborhood"] = cells["neighborhood"].fillna("Unknown")
    lats, lons = cells["lat"].to_numpy(), cells["lon"].to_numpy()
    cells["ej_flag"] = points_in_area(ej_area, lats, lons)
    cells["flood_area_flag"] = points_in_area(flood_area, lats, lons)
    cells["tree_density"] = np.nan
    return cells.loc[:, list(CELL_COLUMNS + EXTRA_COLUMNS)].reset_index(drop=True)


def validate_cells(cells: pd.DataFrame) -> bool:
    """Validate every row as contracts.schemas.Cell; False when the module is missing."""
    try:
        from contracts.schemas import Cell  # type: ignore[import-not-found]
    except ImportError:
        log.warning("contracts.schemas not found yet; skipped Cell validation.")
        return False
    for row in cells.loc[:, list(CELL_COLUMNS)].to_dict("records"):
        record = {k: (None if isinstance(v, float) and np.isnan(v) else
                      (v.item() if hasattr(v, "item") else v)) for k, v in row.items()}
        try:
            Cell.model_validate(record)
        except Exception as exc:
            raise ValueError(f"cell {record['cell_id']} is not a valid Cell: {exc}") from exc
    return True


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not paths.REPORTS_PATH.exists():
        print(f"{paths.REPORTS_PATH} not found. Run `make data` first.", file=sys.stderr)
        return 1
    reports = pd.read_parquet(paths.REPORTS_PATH, columns=["ticket_id", "cell_id", "neighborhood"])
    basins = pd.read_csv(paths.RAW_BASINS_PATH, usecols=["lat", "lon", "OWNER_CODE"], dtype={"OWNER_CODE": str})
    ej_area = load_polygons(paths.RAW_EJ_PATH)
    flood_area = build_flood_area(paths.RAW_FLOOD_PATH)
    write_flood_geojson(flood_area, paths.FLOOD_AREA_GEOJSON_PATH)

    cells = build_cells(basins, reports, ej_area, flood_area)
    missing = set(reports["cell_id"]) - set(cells["cell_id"])
    if missing:
        raise RuntimeError(f"{len(missing)} report cell_ids have no cell")
    validated = validate_cells(cells)
    paths.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(cells, schema=CELLS_SCHEMA, preserve_index=False), paths.CELLS_PATH)

    minx, miny, maxx, maxy = flood_area.bounds
    print("\n=== DrainFast data pipeline: cells ===")
    print(f"cells:              {len(cells)}")
    print(f"  with basins:      {int((cells['basin_count'] > 0).sum())}")
    print(f"  with reports:     {int((cells['report_count'] > 0).sum())}")
    print(f"basins counted:     {int(cells['basin_count'].sum())} of {len(basins)}")
    print("basin_owner:")
    for owner, n in cells["basin_owner"].value_counts().sort_index().items():
        print(f"  {owner:18} {n}")
    print(f"ej_flag:            {int(cells['ej_flag'].sum())}")
    print(f"flood_area_flag:    {int(cells['flood_area_flag'].sum())}")
    print(f"flood area bounds:  lon {minx:.4f} to {maxx:.4f}, lat {miny:.4f} to {maxy:.4f}")
    print(f"Cell validation:    {'passed' if validated else 'skipped (contracts.schemas missing)'}")
    print(f"wrote {paths.CELLS_PATH.relative_to(paths.PROJECT_ROOT)}, "
          f"{paths.FLOOD_AREA_GEOJSON_PATH.relative_to(paths.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
