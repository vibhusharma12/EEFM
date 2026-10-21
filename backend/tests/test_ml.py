"""ML pipeline tests on deterministic synthetic OHLCV data (no network, no Yahoo Finance)."""
import math

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import config, market
from app.main import app
from app.ml import forecasting
from app.ml.errors import InsufficientDataError
from app.ml.features import FEATURE_COLUMNS, WARMUP_ROWS, build_dataset, compute_features, prepare_base_frame
from app.ml.model import (
    chronological_split,
    clear_registry,
    compute_metrics,
    find_model,
    get_or_train,
    naive_baseline_predictions,
    train_and_evaluate,
)

client = TestClient(app, raise_server_exceptions=False)


def synthetic_ohlcv(n=400, seed=0, start="2022-01-03", tz=None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.01, n)
    close = 100 * np.cumprod(1 + rets)
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    volume = rng.integers(1_000_000, 2_000_000, n).astype(float)
    idx = pd.bdate_range(start, periods=n, tz=tz)
    return pd.DataFrame(
        {"Open": close, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx
    )


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setattr(config, "PERSIST_MODELS", True)
    clear_registry()
    market.clear_cache()
    yield
    clear_registry()
    market.clear_cache()


# ------------------------------------------------------------------- 1. feature columns
def test_feature_engineering_creates_expected_columns():
    df = synthetic_ohlcv()
    ds = build_dataset(df)
    assert list(ds.X.columns) == FEATURE_COLUMNS
    for expected in [
        "close_lag_1_rel", "close_lag_2_rel", "close_lag_3_rel", "close_lag_5_rel", "close_lag_10_rel",
        "ret_1", "ret_lag_1", "dist_sma_5", "dist_sma_10", "dist_sma_20", "dist_sma_50",
        "volatility_5", "volatility_10", "volatility_20", "range_pct", "volume_chg",
    ]:
        assert expected in ds.X.columns
    assert np.isfinite(ds.X.to_numpy()).all()  # invalid rows were dropped
    # SMA-50 is first valid on the 50th row => 49 warm-up rows dropped, plus the final (target-less) row
    assert len(ds) == len(df) - (WARMUP_ROWS - 1) - 1


# ------------------------------------------------------------ 2. feature/target alignment
def test_features_and_next_session_target_are_aligned():
    df = synthetic_ohlcv()
    ds = build_dataset(df)
    closes = df["Close"]
    for i in (0, 10, len(ds) - 1):
        t = ds.X.index[i]
        pos = closes.index.get_loc(t)
        assert ds.close.iloc[i] == pytest.approx(closes.iloc[pos])  # close_t
        assert ds.next_close.iloc[i] == pytest.approx(closes.iloc[pos + 1])  # target = close_{t+1}
        assert ds.y.iloc[i] == pytest.approx(closes.iloc[pos + 1] / closes.iloc[pos] - 1)
        # a feature of row t only involves closes at or before t
        assert ds.X["close_lag_1_rel"].iloc[i] == pytest.approx(closes.iloc[pos - 1] / closes.iloc[pos] - 1)
    # the last observed session has features but no target, so it is not a training row
    assert df.index[-1] not in ds.X.index
    assert ds.latest_features.notna().all()


# ----------------------------------------------------------- 3. chronological split
def test_train_and_test_are_chronologically_separated():
    ds = build_dataset(synthetic_ohlcv())
    model = train_and_evaluate(ds, "TEST", "5y")
    assert model.train_period[1] < model.test_period[0]  # ISO dates compare chronologically
    assert model.train_samples + model.test_samples == len(ds)
    assert model.train_samples == chronological_split(len(ds))
    # no shuffling: the test block is the final block of the timeline
    assert model.test_period[1] == ds.X.index[-1].strftime("%Y-%m-%d")


# ------------------------------------------------ 4. no future information in features
def test_features_do_not_use_future_values():
    df = synthetic_ohlcv()
    full = prepare_base_frame(df)
    full_feats = compute_features(full["close"], full["range_pct"], full["volume_chg"])
    for cut in (80, 150, 300):
        part = prepare_base_frame(df.iloc[:cut])  # the world as known at session cut-1
        part_feats = compute_features(part["close"], part["range_pct"], part["volume_chg"])
        pd.testing.assert_series_equal(part_feats.iloc[-1], full_feats.iloc[cut - 1], check_names=False)


def test_model_training_ignores_test_period_data():
    df = synthetic_ohlcv()
    ds = build_dataset(df)
    split = chronological_split(len(ds))
    model_a = train_and_evaluate(ds, "T", "5y")

    # Corrupt everything from the test period onward; the fitted model must not change.
    df2 = df.copy()
    cut_date = ds.X.index[split]
    df2.loc[df2.index > cut_date, ["Close", "High", "Low"]] *= 3.0
    ds2 = build_dataset(df2)
    train_rows = ds.X.index[:split]
    est2 = train_and_evaluate(ds2, "T", "5y").estimator
    probe = ds.X.iloc[:split].tail(20)
    np.testing.assert_allclose(model_a.estimator.predict(probe), est2.predict(ds2.X.loc[probe.index]))
    assert len(train_rows) == split


# ------------------------------------------------------------------- 5. finite metrics
def test_metrics_are_finite_on_valid_input():
    model = train_and_evaluate(build_dataset(synthetic_ohlcv()), "T", "5y")
    for m in (model.metrics, model.baseline_metrics):
        assert math.isfinite(m.mae) and math.isfinite(m.rmse)
        assert m.r2 is not None and math.isfinite(m.r2)
    assert isinstance(model.beat_baseline_mae, bool)
    assert model.beat_baseline_mae == (model.metrics.mae < model.baseline_metrics.mae)


def test_metrics_edge_cases():
    m = compute_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 4.0])
    assert m.mae == pytest.approx(1 / 3) and m.rmse == pytest.approx(math.sqrt(1 / 3))
    assert compute_metrics([5.0, 5.0, 5.0], [5.0, 6.0, 5.0]).r2 is None  # zero variance: undefined, not a crash
    assert compute_metrics([1.0, 2.0, 3.0], [3.0, 1.0, 5.0]).r2 < 0  # negative R2 is preserved
    with pytest.raises(ValueError):
        compute_metrics([1.0, float("nan")], [1.0, 2.0])


# ------------------------------------------------------------------ 6. naive baseline
def test_naive_baseline_predicts_current_close():
    ds = build_dataset(synthetic_ohlcv())
    model = train_and_evaluate(ds, "T", "5y")
    split = model.train_samples
    close_t = ds.close.iloc[split:].to_numpy()
    actual = ds.next_close.iloc[split:].to_numpy()
    np.testing.assert_array_equal(naive_baseline_predictions(close_t), close_t)
    expected_mae = float(np.mean(np.abs(actual - close_t)))
    expected_rmse = float(np.sqrt(np.mean((actual - close_t) ** 2)))
    assert model.baseline_metrics.mae == pytest.approx(expected_mae)
    assert model.baseline_metrics.rmse == pytest.approx(expected_rmse)


# ------------------------------------------------------------------- 7. forecast length
@pytest.mark.parametrize("horizon", [1, 7, 30])
def test_forecast_returns_requested_number_of_values(horizon):
    ds = build_dataset(synthetic_ohlcv())
    model = train_and_evaluate(ds, "T", "5y")
    res = forecasting.forecast(model, ds, horizon)
    assert len(res.prices) == len(res.dates) == horizon
    assert all(math.isfinite(p) and p > 0 for p in res.prices)
    dates = pd.to_datetime(res.dates)
    assert (dates.dayofweek < 5).all()  # no weekends
    assert dates[0] > pd.Timestamp(ds.base.index[-1])
    assert list(dates) == sorted(dates)


def test_future_dates_skip_weekends():
    # 2026-10-23 is a Friday
    assert forecasting.next_trading_dates("2026-10-23", 3) == ["2026-10-26", "2026-10-27", "2026-10-28"]


# -------------------------------------------------------- 8. recursion updates features
def test_recursive_forecast_updates_feature_history():
    ds = build_dataset(synthetic_ohlcv())
    model = train_and_evaluate(ds, "T", "5y")
    res = forecasting.forecast(model, ds, 5)

    # the working history grows by one predicted close per step
    assert res.history_lengths == [res.history_lengths[0] + i for i in range(5)]
    # step 1 starts from the real latest features
    pd.testing.assert_series_equal(res.feature_trace.iloc[0], ds.latest_features.reset_index(drop=True).set_axis(FEATURE_COLUMNS), check_names=False)
    # features are NOT reused: they change from step to step
    assert not res.feature_trace.iloc[0].equals(res.feature_trace.iloc[1])
    last_real = float(ds.base["close"].iloc[-1])
    # step 2's 1-day return is built from the predicted close of step 1
    assert res.feature_trace["ret_1"].iloc[1] == pytest.approx(res.prices[0] / last_real - 1, abs=1e-4)
    assert res.feature_trace["close_lag_1_rel"].iloc[2] == pytest.approx(res.prices[0] / res.prices[1] - 1, abs=1e-4)
    # documented assumption for unobservable inputs
    assert (res.feature_trace["volume_chg"].iloc[1:] == 0).all()


# ------------------------------------------------- 9. invalid horizon / insufficient data
@pytest.mark.parametrize("bad", [0, 31, -1])
def test_invalid_horizon_rejected(bad):
    ds = build_dataset(synthetic_ohlcv())
    model = train_and_evaluate(ds, "T", "5y")
    with pytest.raises(ValueError):
        forecasting.forecast(model, ds, bad)


def test_insufficient_history_is_an_error_not_a_guess():
    with pytest.raises(InsufficientDataError):
        build_dataset(synthetic_ohlcv(n=40))
    ds = build_dataset(synthetic_ohlcv(n=130))  # features OK, but too few rows to train + evaluate
    with pytest.raises(InsufficientDataError):
        train_and_evaluate(ds, "T", "5y")


# ------------------------------------------------------------ model reuse / persistence
def test_model_is_reused_and_tied_to_ticker_and_data():
    df = synthetic_ohlcv()
    m1, _, reused1 = get_or_train("AAA", "5y", df)
    m2, _, reused2 = get_or_train("AAA", "5y", df)
    assert not reused1 and reused2 and m1 is m2

    clear_registry()  # simulate a server restart: the Joblib file is picked up
    m3, _, reused3 = get_or_train("AAA", "5y", df)
    assert reused3 and m3.ticker == "AAA" and m3.data_version == m1.data_version

    m4, _, reused4 = get_or_train("BBB", "5y", df)  # another ticker never reuses AAA's model
    assert not reused4 and m4.ticker == "BBB"

    _, _, reused5 = get_or_train("AAA", "5y", synthetic_ohlcv(n=401))  # new data -> retrain
    assert not reused5


def test_find_model_does_not_claim_untrained():
    assert find_model("ZZZ") is None
    get_or_train("ZZZ", "5y", synthetic_ohlcv())
    found = find_model("ZZZ")
    assert found is not None and found.ticker == "ZZZ"


# ----------------------------------------------------------------------- 10. API
def stub_market(monkeypatch, df):
    monkeypatch.setattr(market, "_download", lambda s, p: (df, {"currency": "USD"}))


def test_predict_api_response_structure(monkeypatch):
    stub_market(monkeypatch, synthetic_ohlcv(tz="America/New_York"))
    r = client.post("/api/predict", json={"ticker": "aapl", "horizon": 7})
    assert r.status_code == 200, r.text
    b = r.json()
    for key in [
        "ticker", "modelName", "generatedAt", "latest", "history", "forecast", "predictedClose", "horizon",
        "metrics", "baselineMetrics", "beatBaselineMae", "trainSamples", "testSamples", "trainPeriod",
        "testPeriod", "featureNames", "featureImportances", "limitations", "assumptions", "period",
    ]:
        assert key in b, key
    assert b["ticker"] == "AAPL" and b["period"] == "5y" and b["horizon"] == 7
    assert len(b["forecast"]) == 7 and b["predictedClose"] == b["forecast"][-1]["predicted"]
    assert set(b["metrics"]) == {"mae", "rmse", "r2"} and set(b["baselineMetrics"]) == {"mae", "rmse", "r2"}
    assert b["latest"]["date"] == b["history"][-1]["date"]
    assert b["trainPeriod"]["end"] < b["testPeriod"]["start"]
    assert b["forecast"][0]["date"] > b["latest"]["date"]
    assert b["featureNames"] == FEATURE_COLUMNS
    assert b["modelReused"] is False

    again = client.post("/api/predict", json={"ticker": "AAPL", "horizon": 30}).json()
    assert again["modelReused"] is True and len(again["forecast"]) == 30  # horizon changes do not retrain


def test_model_info_before_and_after_training(monkeypatch):
    stub_market(monkeypatch, synthetic_ohlcv(tz="America/New_York"))
    before = client.get("/api/model-info/MSFT").json()
    assert before["trained"] is False and before["metrics"] is None
    client.post("/api/predict", json={"ticker": "MSFT", "horizon": 1})
    after = client.get("/api/model-info/MSFT").json()
    assert after["trained"] is True and after["ticker"] == "MSFT"
    assert after["metrics"]["mae"] > 0 and after["trainSamples"] > 0
    assert client.get("/api/model-info/NVDA").json()["trained"] is False  # other tickers unaffected


@pytest.mark.parametrize("horizon", [0, 31, "abc"])
def test_predict_api_rejects_invalid_horizon(horizon):
    r = client.post("/api/predict", json={"ticker": "AAPL", "horizon": horizon})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "body", [{"ticker": "bad!!sym"}, {"ticker": "AAPL", "period": "2w"}]
)
def test_predict_api_validates_ticker_and_period(body):
    assert client.post("/api/predict", json=body).status_code == 400


def test_predict_api_insufficient_data_is_422(monkeypatch):
    stub_market(monkeypatch, synthetic_ohlcv(n=90, tz="America/New_York"))
    r = client.post("/api/predict", json={"ticker": "AAPL", "horizon": 7})
    assert r.status_code == 422 and "history" in r.json()["detail"].lower()


def test_predict_api_upstream_failure_is_not_replaced_by_demo_data(monkeypatch):
    def boom(s, p):
        raise ConnectionError("down")

    monkeypatch.setattr(market, "_download", boom)
    r = client.post("/api/predict", json={"ticker": "AAPL"})
    assert r.status_code == 502 and "forecast" not in r.json()


def test_predict_api_get_method(monkeypatch):
    stub_market(monkeypatch, synthetic_ohlcv(tz="America/New_York"))
    r = client.get("/api/predict", params={"ticker": "AAPL", "horizon": 7})
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == "AAPL"
    assert len(data["forecast"]) == 7

    # Invalid query params
    assert client.get("/api/predict", params={"ticker": "bad!!", "horizon": 7}).status_code == 400
    assert client.get("/api/predict", params={"ticker": "AAPL", "horizon": 50}).status_code == 422

