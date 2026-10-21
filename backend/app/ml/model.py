"""Random Forest training, chronological evaluation, naive baseline, caching and persistence."""
from __future__ import annotations

import logging
import math
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .. import config
from .errors import InsufficientDataError, ModelTrainingError
from .features import FEATURE_COLUMNS, FEATURE_VERSION, Dataset, build_dataset

logger = logging.getLogger("stocksense.ml")

MODEL_NAME = "Random Forest Regressor (scikit-learn)"
TRAIN_FRACTION = 0.8
MIN_TRAIN_SAMPLES = 60
MIN_TEST_SAMPLES = 20

# Hyperparameters (not tuned; chosen to be moderate so the forest does not just memorise noise):
#  - 150 trees: enough to stabilise the average, cheap to train.
#  - max_depth 10 + min_samples_leaf 2: limit tree size to reduce overfitting on small, noisy data.
#  - random_state 42: reproducible results.  n_jobs -1: use all CPU cores.
HYPERPARAMETERS: dict[str, Any] = {
    "n_estimators": 150,
    "max_depth": 10,
    "min_samples_leaf": 2,
    "random_state": 42,
    "n_jobs": -1,
}


@dataclass
class Metrics:
    mae: float
    rmse: float
    r2: float | None  # None when the test targets have zero variance (R2 undefined)


@dataclass
class TrainedModel:
    ticker: str
    period: str
    estimator: RandomForestRegressor
    feature_names: list[str]
    feature_version: str
    data_version: str
    trained_at: str
    last_date: str
    last_close: float
    hyperparameters: dict[str, Any]
    metrics: Metrics  # Random Forest, held-out TEST set only
    baseline_metrics: Metrics  # naive "tomorrow = today", same TEST set
    beat_baseline_mae: bool
    mae_improvement_pct: float | None  # (baseline_mae - rf_mae) / baseline_mae * 100
    train_samples: int
    test_samples: int
    train_period: tuple[str, str]
    test_period: tuple[str, str]
    feature_importances: list[tuple[str, float]] = field(default_factory=list)


# ------------------------------------------------------------------------ evaluation
def compute_metrics(y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series) -> Metrics:
    """MAE / RMSE / R2 with explicit guards so the output is always finite or None."""
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if yt.shape != yp.shape or yt.size == 0:
        raise ValueError("y_true and y_pred must be non-empty and the same length.")
    if not (np.isfinite(yt).all() and np.isfinite(yp).all()):
        raise ValueError("Metrics need finite values.")
    mae = float(mean_absolute_error(yt, yp))
    rmse = float(math.sqrt(mean_squared_error(yt, yp)))
    # R2 divides by the variance of y_true; constant targets would divide by zero.
    r2 = float(r2_score(yt, yp)) if np.ptp(yt) > 0 and yt.size >= 2 else None
    if r2 is not None and not math.isfinite(r2):
        r2 = None
    return Metrics(mae=mae, rmse=rmse, r2=r2)


def naive_baseline_predictions(close_t: pd.Series | np.ndarray) -> np.ndarray:
    """Naive baseline: the next close is predicted to equal the current close."""
    return np.asarray(close_t, dtype=float).copy()


def chronological_split(n: int, train_fraction: float = TRAIN_FRACTION) -> int:
    """Index where the test set starts. Rows [0, idx) train, [idx, n) test. Never shuffled."""
    idx = int(n * train_fraction)
    if idx < MIN_TRAIN_SAMPLES or (n - idx) < MIN_TEST_SAMPLES:
        raise InsufficientDataError(
            f"Not enough usable history to train and evaluate (have {n} labelled sessions; need at least "
            f"{max(math.ceil(round(MIN_TRAIN_SAMPLES / train_fraction, 6)), math.ceil(round(MIN_TEST_SAMPLES / (1 - train_fraction), 6)))}). "
            "Try a longer period such as 5y."
        )
    return idx


def new_estimator() -> RandomForestRegressor:
    return RandomForestRegressor(**HYPERPARAMETERS)


def make_data_version(ds: Dataset) -> str:
    """Identifies the exact data a model was trained on (last session + its close + row count)."""
    base = ds.base
    return f"{base.index[-1].strftime('%Y-%m-%d')}|{len(base)}|{round(float(base['close'].iloc[-1]), 4)}|{FEATURE_VERSION}"


def train_and_evaluate(ds: Dataset, ticker: str, period: str) -> TrainedModel:
    """Fit on the earlier 80 % of the timeline, evaluate on the later 20 % (held out)."""
    split = chronological_split(len(ds))
    X_train, X_test = ds.X.iloc[:split], ds.X.iloc[split:]
    y_train = ds.y.iloc[:split]

    try:
        est = new_estimator()
        est.fit(X_train, y_train)  # the test period is never seen during fitting

        # Convert predicted relative change back to a predicted closing price.
        close_test = ds.close.iloc[split:]
        actual_next_close = ds.next_close.iloc[split:]
        rf_pred = close_test.to_numpy() * (1.0 + est.predict(X_test))
        base_pred = naive_baseline_predictions(close_test)

        rf_metrics = compute_metrics(actual_next_close, rf_pred)
        base_metrics = compute_metrics(actual_next_close, base_pred)
    except InsufficientDataError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Training failed for %s", ticker)
        raise ModelTrainingError("Model training failed. Please try again or use a different ticker.") from exc

    improvement = None
    if base_metrics.mae > 0:
        improvement = (base_metrics.mae - rf_metrics.mae) / base_metrics.mae * 100.0

    importances = sorted(
        zip(FEATURE_COLUMNS, (float(x) for x in est.feature_importances_)), key=lambda kv: kv[1], reverse=True
    )
    dates = ds.X.index
    return TrainedModel(
        ticker=ticker,
        period=period,
        estimator=est,
        feature_names=list(FEATURE_COLUMNS),
        feature_version=FEATURE_VERSION,
        data_version=make_data_version(ds),
        trained_at=datetime.now(timezone.utc).isoformat(),
        last_date=ds.base.index[-1].strftime("%Y-%m-%d"),
        last_close=float(ds.base["close"].iloc[-1]),
        hyperparameters=dict(HYPERPARAMETERS),
        metrics=rf_metrics,
        baseline_metrics=base_metrics,
        beat_baseline_mae=bool(rf_metrics.mae < base_metrics.mae),
        mae_improvement_pct=improvement,
        train_samples=len(X_train),
        test_samples=len(X_test),
        train_period=(dates[0].strftime("%Y-%m-%d"), dates[split - 1].strftime("%Y-%m-%d")),
        test_period=(dates[split].strftime("%Y-%m-%d"), dates[-1].strftime("%Y-%m-%d")),
        feature_importances=importances,
    )


# --------------------------------------------------------------- registry + persistence
_registry: dict[tuple[str, str], TrainedModel] = {}
_registry_lock = threading.Lock()
_train_locks: dict[tuple[str, str], threading.Lock] = {}


def clear_registry() -> None:
    with _registry_lock:
        _registry.clear()
        _train_locks.clear()


def _safe_name(ticker: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", ticker)


def _model_dir() -> Path:
    return Path(config.MODEL_DIR)


def _path_for(ticker: str, period: str) -> Path:
    return _model_dir() / f"{_safe_name(ticker)}__{period}.joblib"


def _persist(model: TrainedModel) -> None:
    if not config.PERSIST_MODELS:
        return
    try:
        _model_dir().mkdir(parents=True, exist_ok=True)
        joblib.dump(asdict_shallow(model), _path_for(model.ticker, model.period))
    except Exception:  # noqa: BLE001 - persistence is best effort; the in-memory model still works
        logger.warning("Could not persist model for %s", model.ticker, exc_info=True)


def asdict_shallow(model: TrainedModel) -> dict[str, Any]:
    """Dataclass -> dict without recursively copying the sklearn estimator."""
    d = {k: getattr(model, k) for k in model.__dataclass_fields__}
    d["metrics"] = asdict(model.metrics)
    d["baseline_metrics"] = asdict(model.baseline_metrics)
    return d


def _from_dict(d: dict[str, Any]) -> TrainedModel:
    d = dict(d)
    d["metrics"] = Metrics(**d["metrics"])
    d["baseline_metrics"] = Metrics(**d["baseline_metrics"])
    d["train_period"] = tuple(d["train_period"])
    d["test_period"] = tuple(d["test_period"])
    return TrainedModel(**d)


def _load_file(path: Path) -> TrainedModel | None:
    """Load a model written by this app. Anything inconsistent is ignored (and retrained)."""
    try:
        if not path.exists():
            return None
        model = _from_dict(joblib.load(path))
        if model.feature_names != FEATURE_COLUMNS or model.feature_version != FEATURE_VERSION:
            return None
        return model
    except Exception:  # noqa: BLE001
        logger.warning("Ignoring unreadable model file %s", path, exc_info=True)
        return None


def get_or_train(ticker: str, period: str, ohlcv: pd.DataFrame) -> tuple[TrainedModel, Dataset, bool]:
    """Return (model, dataset, reused).

    A stored model is reused only if it belongs to the same ticker and period, uses the same
    feature configuration, and was trained on the same data version. Otherwise retrain.
    """
    ds = build_dataset(ohlcv)
    version = make_data_version(ds)
    key = (ticker, period)

    def usable(m: TrainedModel | None) -> bool:
        return (
            m is not None
            and m.ticker == ticker
            and m.period == period
            and m.data_version == version
            and m.feature_names == FEATURE_COLUMNS
        )

    with _registry_lock:
        cached = _registry.get(key)
        lock = _train_locks.setdefault(key, threading.Lock())
    if usable(cached):
        return cached, ds, True  # type: ignore[return-value]

    with lock:  # one training per ticker/period at a time; others wait and reuse the result
        with _registry_lock:
            cached = _registry.get(key)
        if usable(cached):
            return cached, ds, True  # type: ignore[return-value]
        if config.PERSIST_MODELS:
            on_disk = _load_file(_path_for(ticker, period))
            if usable(on_disk):
                with _registry_lock:
                    _registry[key] = on_disk  # type: ignore[assignment]
                return on_disk, ds, True  # type: ignore[return-value]
        model = train_and_evaluate(ds, ticker, period)
        with _registry_lock:
            _registry[key] = model
        _persist(model)
        return model, ds, False


def find_model(ticker: str) -> TrainedModel | None:
    """Most recently trained model for this ticker (memory first, then disk). Never trains."""
    candidates: list[TrainedModel] = []
    with _registry_lock:
        candidates += [m for (t, _), m in _registry.items() if t == ticker]
    if config.PERSIST_MODELS and _model_dir().exists():
        for path in _model_dir().glob(f"{_safe_name(ticker)}__*.joblib"):
            m = _load_file(path)
            if m is not None and m.ticker == ticker:
                candidates.append(m)
    if not candidates:
        return None
    return max(candidates, key=lambda m: m.trained_at)
