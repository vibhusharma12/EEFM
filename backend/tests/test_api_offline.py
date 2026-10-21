"""Offline tests: Yahoo Finance is replaced by a stub, so no network is needed."""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import market
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def make_df(closes, start="2026-10-14", **extra):
    idx = pd.bdate_range(start, periods=len(closes), tz="America/New_York")
    data = {
        "Open": closes,
        "High": [c + 1 for c in closes],
        "Low": [c - 1 for c in closes],
        "Close": closes,
        "Volume": [1000 + i for i in range(len(closes))],
    }
    data.update(extra)
    return pd.DataFrame(data, index=idx)


@pytest.fixture(autouse=True)
def _fresh_cache():
    market.clear_cache()
    yield
    market.clear_cache()


def stub(monkeypatch, fn):
    monkeypatch.setattr(market, "_download", fn)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["version"]


def test_stock_uses_last_two_sessions(monkeypatch):
    # Friday -> Monday gap: change must compare the two sessions, not calendar days.
    df = make_df([100.0, 102.0, 101.0, 110.0, 99.0])
    stub(monkeypatch, lambda s, p: (df, {"longName": "Test Co", "currency": "USD", "fullExchangeName": "NASDAQ"}))
    r = client.get("/api/stock/aapl?period=1mo")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "AAPL" and body["companyName"] == "Test Co"
    assert body["priceBasis"] == "last_close"
    latest = body["latest"]
    assert latest["close"] == 99.0 and latest["previousClose"] == 110.0
    assert latest["change"] == -11.0
    assert latest["changePercent"] == pytest.approx(-10.0)
    assert latest["dayHigh"] == 100.0 and latest["dayLow"] == 98.0
    assert len(body["history"]) == 5


def test_nan_rows_dropped_and_missing_values_null(monkeypatch):
    df = make_df([10.0, float("nan"), 12.0], Volume=[float("nan"), 5, float("nan")])
    stub(monkeypatch, lambda s, p: (df, {}))
    body = client.get("/api/stock/XYZ").json()
    assert len(body["history"]) == 2
    assert body["latest"]["volume"] is None
    assert body["companyName"] is None and body["currency"] is None


def test_single_session_has_no_change(monkeypatch):
    stub(monkeypatch, lambda s, p: (make_df([50.0]), {}))
    latest = client.get("/api/stock/XYZ").json()["latest"]
    assert latest["previousClose"] is None and latest["change"] is None


def test_empty_data_is_404(monkeypatch):
    stub(monkeypatch, lambda s, p: (pd.DataFrame(), {}))
    r = client.get("/api/stock/NOPE")
    assert r.status_code == 404 and "NOPE" in r.json()["detail"]


def test_network_failure_is_502_without_traceback(monkeypatch):
    def boom(s, p):
        raise ConnectionError("secret internal host details")

    stub(monkeypatch, boom)
    r = client.get("/api/stock/AAPL")
    assert r.status_code == 502
    assert "secret" not in r.text and "Traceback" not in r.text


def test_rate_limit_is_429(monkeypatch):
    class YFRateLimitError(Exception):
        pass

    def boom(s, p):
        raise YFRateLimitError("Too Many Requests")

    stub(monkeypatch, boom)
    assert client.get("/api/stock/AAPL").status_code == 429


def test_failures_are_not_cached_but_success_is(monkeypatch):
    calls = {"n": 0}

    def flaky(s, p):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("down")
        return make_df([1.0, 2.0]), {}

    stub(monkeypatch, flaky)
    assert client.get("/api/stock/AAPL").status_code == 502
    assert client.get("/api/stock/AAPL").status_code == 200  # retried, not cached
    assert client.get("/api/stock/AAPL").status_code == 200  # served from cache
    assert calls["n"] == 2


@pytest.mark.parametrize("path", ["/api/stock/bad!!sym", "/api/stock/AAPL?period=2w", "/api/stock/AAPL?period="])
def test_validation_errors(path):
    r = client.get(path)
    assert r.status_code == 400 and isinstance(r.json()["detail"], str)


def test_search_supported_and_manual():
    body = client.get("/api/search", params={"q": "rel"}).json()
    assert body["results"][0]["symbol"] == "RELIANCE.NS"
    assert any(r["source"] == "manual" for r in body["results"])
    assert client.get("/api/search").json()["results"]  # empty query lists suggestions
    assert client.get("/api/search", params={"q": "!!"}).json()["results"] == []


def test_cors_allows_vite_origin():
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
