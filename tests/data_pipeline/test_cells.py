"""Spec 01b-cells-and-flags: grid cells, owners and area flags."""
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st
from shapely.geometry import Point, box

from contracts.cells import cell_center, cell_id
from contracts.schemas import BasinOwner
from data_pipeline.cells import basin_owner_label, build_cells, owner_group, rings_to_polygon, validate_cells

BOSTON_LAT = st.floats(42.22, 42.40, allow_nan=False, allow_infinity=False)
BOSTON_LON = st.floats(-71.20, -70.98, allow_nan=False, allow_infinity=False)
CODES = st.sampled_from(["BWSC", "PRIV", "BPRD", "BHA", "DCR", "MBTA", " bwsc "])


# Feature: 01b-cells-and-flags, Property 1: identical coordinates always give the same cell_id,
# and a cell's center maps back to the same cell
@settings(max_examples=500)
@given(lat=BOSTON_LAT, lon=BOSTON_LON)
def test_cell_id_is_stable(lat: float, lon: float) -> None:
    cid = cell_id(lat, lon)
    assert cid == cell_id(float(lat), float(lon))
    assert cell_id(*cell_center(cid)) == cid


# Feature: 01b-cells-and-flags, Property 2: every report's cell_id exists in cells,
# every basin is counted once, and every row is a valid Cell
@settings(max_examples=100, deadline=None)
@given(
    reports=st.lists(st.tuples(BOSTON_LAT, BOSTON_LON, st.sampled_from(["Roxbury", "Dorchester", "Unknown"])),
                     max_size=25),
    basins=st.lists(st.tuples(BOSTON_LAT, BOSTON_LON, CODES), max_size=25),
)
def test_every_report_cell_exists(reports: list, basins: list) -> None:
    rep = pd.DataFrame(reports, columns=["lat", "lon", "neighborhood"])
    rep["cell_id"] = [cell_id(a, b) for a, b in zip(rep["lat"], rep["lon"])]
    bas = pd.DataFrame(basins, columns=["lat", "lon", "OWNER_CODE"])
    cells = build_cells(bas, rep, ej_area=box(-71.1, 42.3, -71.0, 42.35), flood_area=None)
    assert set(rep["cell_id"]) <= set(cells["cell_id"])
    assert cells["cell_id"].is_unique
    assert int(cells["basin_count"].sum()) == len(bas)
    assert int(cells["report_count"].sum()) == len(rep)
    assert cells["bwsc_share"].between(0, 1).all()
    assert (cells.loc[cells["basin_count"] == 0, "basin_owner"] == "Unknown").all()
    assert not cells["flood_area_flag"].any()
    assert validate_cells(cells)


def test_owner_mapping() -> None:
    assert owner_group("BWSC") == "BWSC"
    assert owner_group(" bwsc ") == "BWSC"
    assert owner_group("BPRD") == owner_group("BHA") == "City"
    assert owner_group("PRIV") == "Private"
    assert owner_group("DCR") == "Private"  # other agencies: not BWSC's or the City's
    assert basin_owner_label(set()) == "Unknown"
    assert basin_owner_label({"BWSC"}) == "BWSC"
    assert basin_owner_label({"BWSC", "Private"}) == "Mixed"
    assert {o.value for o in BasinOwner} >= {"BWSC", "City", "Private", "Mixed", "Unknown"}


def test_neighborhood_is_most_common_report_neighborhood() -> None:
    lat, lon = 42.33, -71.07
    cid = cell_id(lat, lon)
    rep = pd.DataFrame({"cell_id": [cid] * 4, "neighborhood": ["Roxbury", "Dorchester", "Roxbury", "Unknown"]})
    bas = pd.DataFrame({"lat": [lat, lat], "lon": [lon, lon], "OWNER_CODE": ["BWSC", "PRIV"]})
    row = build_cells(bas, rep, None, None).set_index("cell_id").loc[cid]
    assert row["neighborhood"] == "Roxbury"
    assert row["basin_count"] == 2 and row["basin_owner"] == "Mixed" and row["bwsc_share"] == 0.5


def test_rings_clockwise_outer_counterclockwise_hole() -> None:
    outer = [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]  # clockwise
    hole = [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]  # counter-clockwise
    island = [[20, 0], [20, 2], [22, 2], [22, 0], [20, 0]]  # clockwise, separate
    geom = rings_to_polygon([outer, hole, island])
    assert geom.contains(Point(1, 1))
    assert not geom.contains(Point(5, 5))  # inside the hole
    assert geom.contains(Point(21, 1))
    assert abs(geom.area - (100 - 4 + 4)) < 1e-9
