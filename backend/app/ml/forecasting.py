"""Recursive multi-day forecasting with the one-step-ahead Random Forest.

For each future session the loop does:
  1. compute features from the *current working history* (real closes + earlier predictions),
  2. predict the next close,
  3. append that predicted close to the working history,
  4. repeat, so lags, returns, moving averages and volatility are recomputed every step.

Future OHLCV values do not exist, so two features use explicit ASSUMPTIONS (never presented as
observed data):
  * ``range_pct``  : held constant at the mean of the last 20 *observed* sessions.
  * ``volume_chg`` : 0 (volume assumed unchanged).

Errors compound in recursive forecasting: later days are less reliable than the first day.

Future dates skip Saturdays and Sundays only. Exchange holidays are NOT accounted for, so a
forecast date may fall on a day the market is actually closed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .errors import ModelTrainingError
from .features import FEATURE_COLUMNS, RANGE_ASSUMPTION_WINDOW, Dataset, compute_features
from .model import TrainedModel

MIN_HORIZON = 1
MAX_HORIZON = 30
_WORKING_WINDOW = 150  # enough history for the longest feature window (SMA-50) plus slack

DATE_NOTE = "Future dates skip weekends only; exchange holidays are not accounted for."
ASSUMPTION_NOTE = (
    "Future high/low range is assumed equal to the recent 20-session average and future volume "
    "change is assumed to be 0, because future OHLCV values are unknown."
)


@dataclass
class ForecastResult:
    dates: list[str]
    prices: list[float]
    feature_trace: pd.DataFrame  # the exact feature row used at each recursive step
    history_lengths: list[int]  # length of the working close history at each step


def next_trading_dates(last_date: str | pd.Timestamp, horizon: int) -> list[str]:
    """Next ``horizon`` weekdays after ``last_date`` (weekends excluded, holidays not)."""
    start = pd.Timestamp(last_date).tz_localize(None) + pd.Timedelta(days=1)
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(start=start, periods=horizon)]


def forecast(model: TrainedModel, ds: Dataset, horizon: int) -> ForecastResult:
    if not isinstance(horizon, int) or isinstance(horizon, bool) or not (MIN_HORIZON <= horizon <= MAX_HORIZON):
        raise ValueError(f"horizon must be an integer between {MIN_HORIZON} and {MAX_HORIZON}.")

    base = ds.base.iloc[-_WORKING_WINDOW:]
    closes = [float(x) for x in base["close"]]
    ranges = [float(x) for x in base["range_pct"]]
    vol_chg = [float(x) for x in base["volume_chg"]]

    observed_range = ds.base["range_pct"].iloc[-RANGE_ASSUMPTION_WINDOW:]
    assumed_range = float(observed_range.mean())
    assumed_volume_chg = 0.0
    if not math.isfinite(assumed_range):
        raise ModelTrainingError("Could not derive the high-low range assumption for forecasting.")

    prices: list[float] = []
    trace: list[pd.Series] = []
    lengths: list[int] = []

    for _ in range(horizon):
        feats = compute_features(pd.Series(closes), pd.Series(ranges), pd.Series(vol_chg))
        row = feats.iloc[-1]
        if row.isna().any():
            raise ModelTrainingError("Forecast features were incomplete; not enough history.")
        trace.append(row)
        lengths.append(len(closes))

        change = float(model.estimator.predict(row.to_frame().T[FEATURE_COLUMNS])[0])
        next_price = closes[-1] * (1.0 + change)
        if not (math.isfinite(next_price) and next_price > 0):
            raise ModelTrainingError("The model produced an invalid prediction.")

        prices.append(next_price)
        closes.append(next_price)  # predicted close joins the history -> next step's lags/MAs/volatility
        ranges.append(assumed_range)
        vol_chg.append(assumed_volume_chg)

    return ForecastResult(
        dates=next_trading_dates(ds.base.index[-1], horizon),
        prices=[round(p, 4) for p in prices],
        feature_trace=pd.DataFrame(trace).reset_index(drop=True),
        history_lengths=lengths,
    )
