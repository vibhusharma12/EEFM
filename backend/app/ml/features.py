"""Feature engineering for next-session close prediction.

ALIGNMENT (read this first)
---------------------------
Every row ``t`` of the feature table uses only information that is known at the *end* of
session ``t``: closes up to and including ``close_t``, the session-``t`` high/low range and
volume. Nothing after ``t`` is ever used (rolling windows are trailing, lags use positive
shifts only).

The prediction target for row ``t`` is the *next* session's close, ``close_{t+1}``. It is
built with ``close.shift(-1)``, i.e. the target is attached to row ``t`` but is never a
feature. The final observed row has no target (there is no ``t+1`` yet); it is the row
used to start forecasting.

TARGET FORM
-----------
The quantity the model learns is the relative change ``close_{t+1} / close_t - 1`` and it is
converted back to a price with ``close_t * (1 + predicted_change)``. This still predicts the
next close, but tree models cannot extrapolate beyond the target range seen in training;
with raw prices a stock trading at an all-time high would be capped near its old maximum.
All features are therefore scale-free (ratios / returns) rather than raw price levels.

FEATURES THAT NEED FUTURE HIGH / LOW / VOLUME
---------------------------------------------
``range_pct`` (high-low range) and ``volume_chg`` need OHLCV data that does not exist for
future sessions. During recursive forecasting they are *assumptions*, not observations:
``range_pct`` is held at the average of the last 20 observed sessions and ``volume_chg`` is
set to 0 (volume assumed unchanged). See ``forecasting.py``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .errors import InsufficientDataError

FEATURE_VERSION = "v1"
LAG_PERIODS = (1, 2, 3, 5, 10)
RETURN_LAGS = (1, 2, 3, 5)
SMA_WINDOWS = (5, 10, 20, 50)
VOL_WINDOWS = (5, 10, 20)
RANGE_ASSUMPTION_WINDOW = 20

FEATURE_COLUMNS: list[str] = (
    [f"close_lag_{k}_rel" for k in LAG_PERIODS]  # close_{t-k} / close_t - 1
    + ["ret_1"]  # close_t / close_{t-1} - 1
    + [f"ret_lag_{k}" for k in RETURN_LAGS]  # return of session t-k
    + [f"dist_sma_{w}" for w in SMA_WINDOWS]  # close_t / SMA_w(t) - 1
    + [f"volatility_{w}" for w in VOL_WINDOWS]  # std of the last w daily returns
    + ["range_pct", "volume_chg"]
)

# First usable row needs 50 closes for SMA-50, so ~49 warm-up rows are lost.
WARMUP_ROWS = max(SMA_WINDOWS)


def prepare_base_frame(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Clean raw OHLCV into the three base series the features are derived from.

    Input columns: Close, High, Low, Volume (index = trading dates).
    Output columns: ``close``, ``range_pct`` and ``volume_chg``.
    """
    required = {"Close", "High", "Low", "Volume"}
    missing = required - set(ohlcv.columns)
    if missing:
        raise InsufficientDataError(f"Historical data is missing columns: {', '.join(sorted(missing))}.")

    df = ohlcv[["Close", "High", "Low", "Volume"]].astype(float)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]

    base = pd.DataFrame(index=df.index)
    base["close"] = df["Close"]
    base["range_pct"] = (df["High"] - df["Low"]) / df["Close"]  # Close > 0 guaranteed above

    # Volume change vs the previous session. Unknown / zero previous volume => no information => 0.
    prev_vol = df["Volume"].shift(1)
    valid = (prev_vol > 0) & df["Volume"].notna()
    chg = pd.Series(0.0, index=df.index)
    chg[valid] = df["Volume"][valid] / prev_vol[valid] - 1.0
    base["volume_chg"] = chg.clip(-0.9, 3.0)  # tame extreme volume spikes
    return base


def compute_features(close: pd.Series, range_pct: pd.Series, volume_chg: pd.Series) -> pd.DataFrame:
    """Compute FEATURE_COLUMNS for every row; early rows are NaN until windows fill.

    This single function is used for both training and recursive forecasting so the two
    can never drift apart. All operations are backward-looking.
    """
    f = pd.DataFrame(index=close.index)
    ret = close.pct_change()  # close_t / close_{t-1} - 1  (NaN on the first row)

    for k in LAG_PERIODS:
        f[f"close_lag_{k}_rel"] = close.shift(k) / close - 1.0
    f["ret_1"] = ret
    for k in RETURN_LAGS:
        f[f"ret_lag_{k}"] = ret.shift(k)
    for w in SMA_WINDOWS:
        f[f"dist_sma_{w}"] = close / close.rolling(w, min_periods=w).mean() - 1.0
    for w in VOL_WINDOWS:
        f[f"volatility_{w}"] = ret.rolling(w, min_periods=w).std()
    f["range_pct"] = range_pct
    f["volume_chg"] = volume_chg
    return f[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)


@dataclass
class Dataset:
    """Supervised dataset. Row i: features at session t -> target built from close_{t+1}."""

    X: pd.DataFrame  # features known at the end of session t
    y: pd.Series  # close_{t+1} / close_t - 1
    close: pd.Series  # close_t
    next_close: pd.Series  # close_{t+1} (the actual target price)
    # The last observed session (features only, no target yet); used to start forecasts.
    latest_features: pd.Series
    base: pd.DataFrame

    def __len__(self) -> int:
        return len(self.X)


def build_dataset(ohlcv: pd.DataFrame) -> Dataset:
    base = prepare_base_frame(ohlcv)
    feats = compute_features(base["close"], base["range_pct"], base["volume_chg"])

    next_close = base["close"].shift(-1)  # attaches close_{t+1} to row t; NaN on the last row
    target = next_close / base["close"] - 1.0

    full = feats.copy()
    full["_target"] = target
    full["_close"] = base["close"]
    full["_next_close"] = next_close

    latest = feats.iloc[-1] if len(feats) else None
    if latest is None or latest.isna().any():
        raise InsufficientDataError(
            f"Not enough history to compute all features for the latest session "
            f"(need at least {WARMUP_ROWS + 1} valid trading days)."
        )

    train_rows = full.dropna()  # drops warm-up rows and the final row (no next close yet)
    if not np.isfinite(train_rows["_target"]).all():
        train_rows = train_rows[np.isfinite(train_rows["_target"])]

    return Dataset(
        X=train_rows[FEATURE_COLUMNS],
        y=train_rows["_target"],
        close=train_rows["_close"],
        next_close=train_rows["_next_close"],
        latest_features=latest,
        base=base,
    )


def finite(value: float | None) -> float | None:
    """Convert NaN / inf to None so JSON serialisation stays valid."""
    if value is None:
        return None
    v = float(value)
    return v if math.isfinite(v) else None
