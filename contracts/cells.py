"""Shared 100 m grid. The only definition of a cell; never redefine it elsewhere."""
import math

LAT0, LON0 = 42.22, -71.20
DLAT = 100 / 111320
DLON = 100 / (111320 * math.cos(math.radians(42.32)))


def cell_id(lat: float, lon: float) -> str:
    """Return the id of the ~100 m cell containing (lat, lon)."""
    return f"c_{int((lat - LAT0) // DLAT)}_{int((lon - LON0) // DLON)}"


def cell_center(cid: str) -> tuple[float, float]:
    """Return the (lat, lon) center of a cell id produced by cell_id."""
    _, r, c = cid.split("_")
    return LAT0 + (int(r) + 0.5) * DLAT, LON0 + (int(c) + 0.5) * DLON
