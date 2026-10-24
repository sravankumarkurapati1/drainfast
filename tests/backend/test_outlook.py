"""Pre-storm look-ahead: the forecast decides when the brief shows (GET /outlook)."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend import sources
from backend.app import app

TUESDAY = date(2026, 10, 27)


def _grid(storm_day: str, mm: float) -> list[dict]:
    """Dry week except `mm` of rain in a 6 h block at noon (EDT) on storm_day."""
    days = ["2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"]
    values = [{"validTime": f"{d}T04:00:00+00:00/PT6H", "value": 0.0} for d in days]
    values.append({"validTime": f"{storm_day}T16:00:00+00:00/PT6H", "value": mm})
    return values


def test_storm_thursday_turns_brief_on():
    out = _outlook_with(_grid("2026-10-29", 38.1))  # 1.5 in on Thursday
    assert out.next_storm == {"date": "2026-10-29", "rain_in": 1.5}
    assert out.brief_active is True and out.check_by == "2026-10-28" and out.fallback is False


def test_dry_week_has_no_storm():
    out = _outlook_with(_grid("2026-10-29", 2.0))  # 0.08 in, below 0.5
    assert out.next_storm is None and out.brief_active is False


def test_storm_beyond_lookahead_is_shown_but_brief_stays_off():
    out = _outlook_with(_grid("2026-11-02", 25.4))  # 1.0 in, 6 days out
    assert out.next_storm["date"] == "2026-11-02" and out.brief_active is False


def test_fallback_mode_makes_no_call():
    def never(*_a):
        raise AssertionError("must not fetch in fallback mode")
    out = sources.storm_outlook(TUESDAY, 0.5, 3, fetch=never)
    assert out.fallback is True and out.brief_active is False


def _outlook_with(values: list[dict]) -> sources.StormOutlook:
    sources._grid_cache.clear()
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DRAINFAST_FALLBACK", "0")
        mp.setattr(sources, "_grid_values", lambda _fetch: values)
        return sources.storm_outlook(TUESDAY, 0.5, 3)


def test_outlook_endpoint_message(monkeypatch):
    monkeypatch.setenv("DRAINFAST_FALLBACK", "0")
    monkeypatch.setattr(app_module, "_today", lambda: TUESDAY)
    monkeypatch.setattr(sources, "_grid_values", lambda _fetch: _grid("2026-10-29", 38.1))
    body = TestClient(app).get("/outlook").json()
    assert body["message"] == "Storm expected Thursday, about 1.5 in. Check these locations first, by Wednesday."
    assert body["brief_active"] is True and body["next_storm"] == {"date": "2026-10-29", "rain_in": 1.5}

    monkeypatch.setattr(sources, "_grid_values", lambda _fetch: _grid("2026-10-29", 0.0))
    assert TestClient(app).get("/outlook").json()["message"] == "No storm in the forecast. Routine cleaning continues."


def test_brief_items_carry_no_rain_factor(empty_demo_dir):
    body = TestClient(app).get("/brief", params={"date": "2099-01-01", "crews": 2, "forecast_rain_in": 2.0}).json()
    assert body["forecast_rain_in"] == 2.0  # rain shown once, at the top
    for item in body["items"]:
        assert not any("rain" in f["factor"].lower().replace("drain", "") for f in item["factors"])
