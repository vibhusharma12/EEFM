from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Serializes snake_case fields as camelCase to match the frontend types."""

    # protected_namespaces=() lets fields such as `model_name` exist without a pydantic warning.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, protected_namespaces=())


class HealthResponse(CamelModel):
    status: Literal["ok"]
    version: str
    time: str


class OhlcvPoint(CamelModel):
    date: str  # YYYY-MM-DD, exchange-local trading day
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[int] = None


class LatestStats(CamelModel):
    """Statistics for the most recent trading session in the data."""

    date: str
    close: float
    previous_close: Optional[float] = None
    previous_date: Optional[str] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    open: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None


class StockResponse(CamelModel):
    ticker: str
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    period: str
    latest: LatestStats
    # "last_close": the session is finished, `latest.close` is an official close.
    # "intraday_delayed": the session is still in progress, so `latest.close` is
    # the most recent (delayed) price rather than a final close.
    price_basis: Literal["last_close", "intraday_delayed"]
    last_trade_time: Optional[str] = None
    fetched_at: str
    data_source: str = "Yahoo Finance (via yfinance)"
    history: list[OhlcvPoint]


class SearchResult(CamelModel):
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    source: Literal["supported_list", "manual"]


class SearchResponse(CamelModel):
    query: str
    results: list[SearchResult]
    note: str


class ErrorResponse(BaseModel):
    detail: str


# ------------------------------------------------------------------ Phase 3: prediction
class PredictRequest(CamelModel):
    ticker: str = Field(min_length=1, max_length=15)
    period: str = "5y"
    horizon: int = Field(default=7, ge=1, le=30, description="Trading days to forecast (1-30).")


class ClosePoint(CamelModel):
    date: str
    close: float


class ForecastPoint(CamelModel):
    date: str
    predicted: float


class MetricSet(CamelModel):
    mae: float
    rmse: float
    # None when R2 is undefined (constant test targets). May legitimately be negative.
    r2: Optional[float] = None


class DateRange(CamelModel):
    start: str
    end: str


class FeatureImportance(CamelModel):
    feature: str
    importance: float


class PredictResponse(CamelModel):
    ticker: str
    model_name: str
    generated_at: str
    currency: Optional[str] = None
    period: str
    horizon: int
    latest: ClosePoint  # latest historical close and its date
    history: list[ClosePoint]  # actual closing prices (most recent sessions)
    forecast: list[ForecastPoint]
    predicted_close: float  # forecast for the last day of the horizon
    # Held-out TEST-set results only (never training-set performance).
    metrics: MetricSet
    baseline_metrics: MetricSet
    baseline_name: str
    beat_baseline_mae: bool
    mae_improvement_pct: Optional[float] = None  # positive = Random Forest has lower MAE
    train_samples: int
    test_samples: int
    # Dates of the sessions whose features are used; each target is the following session's close.
    train_period: DateRange
    test_period: DateRange
    feature_names: list[str]
    feature_importances: list[FeatureImportance]
    model_reused: bool  # True when a previously trained model for identical data was reused
    trained_at: str
    data_version: str
    assumptions: list[str]
    limitations: str


class ModelInfoResponse(CamelModel):
    ticker: str
    trained: bool
    message: Optional[str] = None
    model_name: Optional[str] = None
    period: Optional[str] = None
    trained_at: Optional[str] = None
    data_version: Optional[str] = None
    feature_version: Optional[str] = None
    hyperparameters: Optional[dict[str, int]] = None
    feature_names: list[str] = []
    feature_importances: list[FeatureImportance] = []
    metrics: Optional[MetricSet] = None
    baseline_metrics: Optional[MetricSet] = None
    beat_baseline_mae: Optional[bool] = None
    mae_improvement_pct: Optional[float] = None
    train_samples: Optional[int] = None
    test_samples: Optional[int] = None
    train_period: Optional[DateRange] = None
    test_period: Optional[DateRange] = None
