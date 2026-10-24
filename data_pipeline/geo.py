"""Point-in-area checks for EJ block groups and the flood area."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely import contains_xy, make_valid, prepare
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def load_polygons(path: Path) -> BaseGeometry:
    """Union of every polygon in a lon/lat GeoJSON FeatureCollection."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    geoms = [make_valid(shape(f["geometry"])) for f in data["features"] if f.get("geometry")]
    area = unary_union(geoms)
    prepare(area)
    return area


def points_in_area(area: BaseGeometry | None, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Boolean array: True where (lon, lat) lies inside the area. All False when area is None."""
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)
    if area is None or len(lats) == 0:
        return np.zeros(len(lats), dtype=bool)
    return np.asarray(contains_xy(area, lons, lats), dtype=bool)
