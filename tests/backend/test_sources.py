"""Unit tests for backend/sources.py with canned API payloads (no network)."""
import json
from datetime import date, timedelta

import pytest

from backend import sources


def test_parse_duration():
    assert sources.parse_duration("PT6H") == timedelta(hours=6)
    assert sources.parse_duration("P1D") == timedelta(days=1)
    assert sources.parse_duration("P1DT12H") == timedelta(days=1, hours=12)
    with pytest.raises(ValueError):
        sources.parse_duration("P")


def test_rain_split_across_local_midnight():
    # 6 h starting 02:00 UTC Oct 25 = 22:00 EDT Oct 24 -> 2 h on Oct 24, 4 h on Oct 25.
    values = [{"validTime": "2026-10-25T02:00:00+00:00/PT6H", "value": 25.4 * 6}]
    assert sources.rain_in_on_day(values, date(2026, 10, 24)) == pytest.approx(2.0)
    assert sources.rain_in_on_day(values, date(2026, 10, 25)) == pytest.approx(4.0)
    assert sources.rain_in_on_day(values, date(2026, 10, 26)) == 0.0


def _fake_nws(url, _params):
    if url == sources.NWS_POINT:
        return {"properties": {"forecastGridData": "https://api.weather.gov/gridpoints/BOX/71,90"}}
    return {"properties": {"quantitativePrecipitation": {"values": [
        # 05:00 UTC = 00:00 EST (DST ended Nov 1), so all 12 h fall on Nov 2.
        {"validTime": "2026-11-02T05:00:00+00:00/PT12H", "value": 12.7},
        {"validTime": "2026-11-02T17:00:00+00:00/PT6H", "value": None}]}}}


def test_rain_forecast_parses_grid(monkeypatch):
    monkeypatch.setenv("DRAINFAST_FALLBACK", "0")
    sources._rain_cache.clear()
    out = sources.rain_forecast(date(2026, 11, 2), fetch=_fake_nws)
    assert out.fallback is False and out.rain_in == pytest.approx(0.5)


def test_rain_forecast_network_failure_is_fallback(monkeypatch):
    monkeypatch.setenv("DRAINFAST_FALLBACK", "0")
    sources._rain_cache.clear()

    def boom(*_a):
        raise OSError("down")
    out = sources.rain_forecast(date(2026, 11, 3), fetch=boom)
    assert out.fallback is True and out.rain_in is None


def test_fallback_env_makes_no_calls():
    def never(*_a):
        raise AssertionError("must not fetch in fallback mode")
    assert sources.rain_forecast(date(2026, 11, 4), fetch=never).fallback is True
    assert sources.tide_outlook(date(2026, 11, 4), fetch=never).fallback is True


def test_tide_outlook_flag_uses_threshold(monkeypatch, empty_demo_dir):
    monkeypatch.setenv("DRAINFAST_FALLBACK", "0")
    (empty_demo_dir / "tide_threshold.json").write_text(json.dumps({"threshold_ft": 11.5}))
    preds = {"predictions": [{"t": "2026-11-05 10:00", "v": "11.9", "type": "H"},
                             {"t": "2026-11-05 16:10", "v": "0.4", "type": "L"}]}
    out = sources.tide_outlook(date(2026, 11, 5), fetch=lambda *_a: preds)
    assert out.high_tide_flag is True and out.max_ft_mllw == 11.9 and out.fallback is False


def test_tide_threshold_falls_back_to_raw_history(empty_demo_dir):
    from backend.store import tide_threshold_ft
    value = tide_threshold_ft()  # no tide_threshold.json in the empty demo dir
    assert value is not None and 8.0 < value < 16.0
    (empty_demo_dir / "tide_threshold.json").write_text("11.0")
    assert tide_threshold_ft() == 11.0  # the model owner's file wins
