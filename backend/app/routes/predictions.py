"""Prediction endpoints. All ML logic lives in app.ml; this module only validates and maps data."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from .. import market
from ..ml import forecasting
from ..ml.features import finite
from ..ml.model import MODEL_NAME, Metrics, TrainedModel, find_model, get_or_train
from ..schemas import (
    ClosePoint,
    DateRange,
    ErrorResponse,
    FeatureImportance,
    ForecastPoint,
    MetricSet,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
    StockResponse,
)
from ..symbols import normalize_ticker

router = APIRouter(prefix="/api", tags=["predictions"])

BASELINE_NAME = "Naive baseline (tomorrow's close = today's close)"
HISTORY_POINTS_RETURNED = 120

LIMITATIONS = (
    "Statistical estimate from past prices only; it ignores news, earnings, macro events and "
    "liquidity. Metrics come from one chronological hold-out window and may not hold in other "
    "periods. Multi-day forecasts are recursive, so errors compound and later days are less "
    "reliable. Future dates skip weekends only (exchange holidays are not modelled). Not financial advice."
)

_ERRORS = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}


def ohlcv_from_stock(stock: StockResponse) -> pd.DataFrame:
    """Convert the Phase 2 market-data response into the OHLCV frame the ML code expects."""
    idx = pd.DatetimeIndex([pd.Timestamp(p.date) for p in stock.history])
    return pd.DataFrame(
        {
            "Close": [p.close for p in stock.history],
            "High": [p.high if p.high is not None else float("nan") for p in stock.history],
            "Low": [p.low if p.low is not None else float("nan") for p in stock.history],
            "Volume": [float(p.volume) if p.volume is not None else float("nan") for p in stock.history],
        },
        index=idx,
    )


def _metric_set(m: Metrics) -> MetricSet:
    return MetricSet(mae=m.mae, rmse=m.rmse, r2=finite(m.r2))


def _importances(model: TrainedModel) -> list[FeatureImportance]:
    return [FeatureImportance(feature=f, importance=round(v, 6)) for f, v in model.feature_importances]


@router.post("/predict", response_model=PredictResponse, responses=_ERRORS)
def predict(req: PredictRequest) -> PredictResponse:
    """Train (or reuse) a Random Forest for the ticker, evaluate it on held-out data, and forecast."""
    symbol = normalize_ticker(req.ticker)
    if symbol is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker symbol. Use letters, numbers, '.' or '-' (for example AAPL or RELIANCE.NS).",
        )
    period = req.period.strip().lower()
    if period not in market.ALLOWED_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Supported periods: {', '.join(market.ALLOWED_PERIODS)}.",
        )

    stock = market.get_stock(symbol, period)  # Phase 2 service: validation, caching, error mapping
    ohlcv = ohlcv_from_stock(stock)

    # InsufficientDataError / ModelTrainingError are mapped to HTTP errors in main.py.
    model, ds, reused = get_or_train(symbol, period, ohlcv)
    result = forecasting.forecast(model, ds, req.horizon)

    closes = ds.base["close"]
    history = [ClosePoint(date=d.strftime("%Y-%m-%d"), close=round(float(c), 4)) for d, c in closes.tail(HISTORY_POINTS_RETURNED).items()]
    forecast = [ForecastPoint(date=d, predicted=p) for d, p in zip(result.dates, result.prices)]

    return PredictResponse(
        ticker=symbol,
        model_name=MODEL_NAME,
        generated_at=datetime.now(timezone.utc).isoformat(),
        currency=stock.currency,
        period=period,
        horizon=req.horizon,
        latest=history[-1],
        history=history,
        forecast=forecast,
        predicted_close=forecast[-1].predicted,
        metrics=_metric_set(model.metrics),
        baseline_metrics=_metric_set(model.baseline_metrics),
        baseline_name=BASELINE_NAME,
        beat_baseline_mae=model.beat_baseline_mae,
        mae_improvement_pct=None if model.mae_improvement_pct is None else round(model.mae_improvement_pct, 2),
        train_samples=model.train_samples,
        test_samples=model.test_samples,
        train_period=DateRange(start=model.train_period[0], end=model.train_period[1]),
        test_period=DateRange(start=model.test_period[0], end=model.test_period[1]),
        feature_names=model.feature_names,
        feature_importances=_importances(model),
        model_reused=reused,
        trained_at=model.trained_at,
        data_version=model.data_version,
        assumptions=[forecasting.ASSUMPTION_NOTE, forecasting.DATE_NOTE],
        limitations=LIMITATIONS,
    )


@router.get("/predict", response_model=PredictResponse, responses=_ERRORS)
def predict_get(
    ticker: str = Query(..., min_length=1, max_length=15),
    period: str = Query("5y"),
    horizon: int = Query(7, ge=1, le=30),
) -> PredictResponse:
    """Convenience GET endpoint supporting query parameters (ticker, period, horizon)."""
    return predict(PredictRequest.model_construct(ticker=ticker, period=period, horizon=horizon))



@router.get("/model-info/{ticker}", response_model=ModelInfoResponse, responses=_ERRORS)
def model_info(ticker: str) -> ModelInfoResponse:
    """Metadata and held-out evaluation of an already-trained model. Never trains one."""
    symbol = normalize_ticker(ticker)
    if symbol is None:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol.")
    model = find_model(symbol)
    if model is None:
        return ModelInfoResponse(
            ticker=symbol,
            trained=False,
            message=f"No model has been trained for {symbol} yet. Run a prediction to train one.",
        )
    return ModelInfoResponse(
        ticker=symbol,
        trained=True,
        model_name=MODEL_NAME,
        period=model.period,
        trained_at=model.trained_at,
        data_version=model.data_version,
        feature_version=model.feature_version,
        hyperparameters={k: int(v) for k, v in model.hyperparameters.items()},
        feature_names=model.feature_names,
        feature_importances=_importances(model),
        metrics=_metric_set(model.metrics),
        baseline_metrics=_metric_set(model.baseline_metrics),
        beat_baseline_mae=model.beat_baseline_mae,
        mae_improvement_pct=None if model.mae_improvement_pct is None else round(model.mae_improvement_pct, 2),
        train_samples=model.train_samples,
        test_samples=model.test_samples,
        train_period=DateRange(start=model.train_period[0], end=model.train_period[1]),
        test_period=DateRange(start=model.test_period[0], end=model.test_period[1]),
    )
