"""API tests in fallback mode, running on backend/fixtures (empty data/demo)."""
from fastapi.testclient import TestClient

from backend.app import app
from mcp_server.server import TOOLS, run_tool

client = TestClient(app)


def test_health_reports_fallback(empty_demo_dir):
    assert client.get("/health").json() == {"status": "ok", "fallback": True}


def test_brief_evidence_on_fixtures(empty_demo_dir):
    r = client.get("/brief", params={"date": "2099-01-01", "crews": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["fallback_mode"] is True and body["forecast_rain_in"] == 1.0
    assert all(item["evidence_ticket_ids"] for item in body["items"])


def test_backlog_evidence_and_status_unclear(empty_demo_dir):
    items = client.get("/backlog", params={"limit": 50}).json()
    assert all(i["evidence_ticket_ids"] for i in items)
    assert all(i["status_label"] == "Status unclear" for i in items if i["note_blank"])


def test_validation_error_detail_is_a_string(empty_demo_dir):
    r = client.get("/brief", params={"date": "not-a-date", "crews": 0})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_unknown_cell_is_404(empty_demo_dir):
    r = client.get("/cells/c_0_0/history")
    assert r.status_code == 404 and isinstance(r.json()["detail"], str)


def test_backtest_and_rain_trend_load(empty_demo_dir):
    assert client.get("/backtest").status_code == 200
    assert client.get("/rain-trend").status_code == 200


def test_mcp_tools_share_backend_functions(empty_demo_dir):
    assert {t.name for t in TOOLS} == {"rain_forecast", "tide_outlook", "cell_history"}
    assert run_tool("rain_forecast", {"date": "2026-11-01"})["fallback"] is True
    cid = client.get("/backlog").json()[0]["cell_id"]
    hist = run_tool("cell_history", {"cell_id": cid})
    assert hist["total_reports"] == len(client.get(f"/cells/{cid}/history").json())


def test_brief_rain_override(empty_demo_dir):
    future = client.get("/brief", params={"date": "2099-01-01", "crews": 2, "forecast_rain_in": 2.5}).json()
    assert future["forecast_rain_in"] == 2.5
    past = client.get("/brief", params={"date": "2024-01-11", "crews": 2, "forecast_rain_in": 0.3}).json()
    assert past["forecast_rain_in"] == 0.3
    bad = client.get("/brief", params={"date": "2099-01-01", "crews": 2, "forecast_rain_in": -1})
    assert bad.status_code == 422


def test_live_mode_never_invents_rain(monkeypatch):
    """With fallback off and NWS down, /brief for an upcoming date says so (503), no 1.0 in default."""
    monkeypatch.setenv("DRAINFAST_FALLBACK", "0")
    r = client.get("/brief", params={"date": "2099-01-01", "crews": 2})  # network is blocked in tests
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]
    ok = client.get("/brief", params={"date": "2099-01-01", "crews": 2, "forecast_rain_in": 1.2})
    assert ok.status_code == 200 and ok.json()["forecast_rain_in"] == 1.2


def test_live_mode_never_serves_sample_data(monkeypatch, empty_demo_dir):
    monkeypatch.setenv("DRAINFAST_FALLBACK", "0")
    assert client.get("/backtest").json() == []  # missing file -> empty, not fixtures
