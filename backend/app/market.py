"""Yahoo Finance access (via yfinance) with validation, error mapping and caching."""
from __future__ import annotations

import logging
import math
import threading
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from . import config
from .schemas import LatestStats, OhlcvPoint, StockResponse

logger = logging.getLogger("stocksense.market")

# API period -> yfinance period (identical today, kept explicit as the allow-list).
ALLOWED_PERIODS: dict[str, str] = {
    "1mo": "1mo",
    "3mo": "3mo",
    "6mo": "6mo",
    "1y": "1y",
    "5y": "5y",
}


# --------------------------------------------------------------------------- errors
class MarketDataError(Exception):
    """An error whose message is safe to show to API clients."""

    status_code = 502

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class TickerNotFound(MarketDataError):
    status_code = 404


class RateLimited(MarketDataError):
    status_code = 429


class UpstreamUnavailable(MarketDataError):
    status_code = 502


class UpstreamTimeout(MarketDataError):
    status_code = 504


def _classify(exc: Exception, symbol: str) -> MarketDataError:
    """Translate any yfinance / network exception into a safe, user-facing error."""
    name = type(exc).__name__
    text = str(exc).lower()
    if name == "YFRateLimitError" or "too many requests" in text or "rate limit" in text or "429" in text:
        return RateLimited("Yahoo Finance is rate limiting requests. Please wait a minute and try again.")
    if name in {"YFPricesMissingError", "YFTzMissingError", "YFTickerMissingError", "YFInvalidPeriodError"} or any(
        s in text for s in ("no data found", "delisted", "no price data", "symbol may be delisted", "invalid isin")
    ):
        return TickerNotFound(f"No market data found for '{symbol}'. Check the ticker symbol (e.g. AAPL, RELIANCE.NS).")
    if "timed out" in text or "timeout" in text or "timeout" in name.lower():
        return UpstreamTimeout("Yahoo Finance took too long to respond. Please try again.")
    return UpstreamUnavailable("Could not reach Yahoo Finance. Check the server's internet connection and try again.")


# ------------------------------------------------------------------------- helpers
def _num(value: Any, digits: int = 4) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, digits)


def _int(value: Any) -> int | None:
    f = _num(value, 0)
    return None if f is None else int(f)


def _to_utc(value: Any) -> datetime | None:
    """Accepts epoch seconds, datetime or Timestamp."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        ts = pd.Timestamp(value)
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        return ts.to_pydatetime()
    except Exception:  # noqa: BLE001 - metadata is best effort only
        return None


def _is_session_in_progress(meta: dict[str, Any]) -> bool:
    try:
        regular = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
        start, end = _to_utc(regular.get("start")), _to_utc(regular.get("end"))
        if start and end:
            return start <= datetime.now(timezone.utc) < end
    except Exception:  # noqa: BLE001
        pass
    return False


# ----------------------------------------------------------------------- upstream
def _download(symbol: str, period: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch raw daily bars + metadata. Isolated so tests can replace it."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(
        period=ALLOWED_PERIODS[period],
        interval="1d",
        auto_adjust=False,  # raw closes, matching the prices Yahoo displays
        actions=False,
        timeout=config.UPSTREAM_TIMEOUT,
        raise_errors=True,
    )
    meta: dict[str, Any] = {}
    if df is not None and not df.empty:
        try:
            meta = dict(ticker.history_metadata or {})
        except Exception:  # noqa: BLE001 - metadata (name/currency) is optional
            logger.warning("No metadata for %s", symbol)
    return df, meta


def build_stock_response(symbol: str, period: str, df: pd.DataFrame, meta: dict[str, Any]) -> StockResponse:
    if df is None or df.empty or "Close" not in df:
        raise TickerNotFound(f"No market data found for '{symbol}'. Check the ticker symbol (e.g. AAPL, RELIANCE.NS).")

    df = df.dropna(subset=["Close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if df.empty:
        raise TickerNotFound(f"Yahoo Finance returned no usable prices for '{symbol}'.")

    history = [
        OhlcvPoint(
            date=ts.strftime("%Y-%m-%d"),
            open=_num(row.get("Open")),
            high=_num(row.get("High")),
            low=_num(row.get("Low")),
            close=_num(row["Close"]),  # type: ignore[arg-type]  # NaN rows already dropped
            volume=_int(row.get("Volume")),
        )
        for ts, row in df.iterrows()
    ]

    # Daily change always uses the two most recent trading sessions in the data,
    # never today's calendar date, so weekends and holidays are handled naturally.
    last = history[-1]
    prev = history[-2] if len(history) >= 2 else None
    change = pct = None
    if prev is not None and prev.close:
        change = round(last.close - prev.close, 4)
        pct = round(change / prev.close * 100, 4)

    latest = LatestStats(
        date=last.date,
        close=last.close,
        previous_close=prev.close if prev else None,
        previous_date=prev.date if prev else None,
        change=change,
        change_percent=pct,
        open=last.open,
        day_high=last.high,
        day_low=last.low,
        volume=last.volume,
    )

    trade_time = _to_utc(meta.get("regularMarketTime"))
    return StockResponse(
        ticker=symbol,
        company_name=meta.get("longName") or meta.get("shortName") or None,
        exchange=meta.get("fullExchangeName") or meta.get("exchangeName") or None,
        currency=meta.get("currency") or None,
        period=period,
        latest=latest,
        price_basis="intraday_delayed" if _is_session_in_progress(meta) else "last_close",
        last_trade_time=trade_time.isoformat() if trade_time else None,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        history=history,
    )


# -------------------------------------------------------------------------- cache
_MAX_CACHE_ENTRIES = 256
_cache: dict[tuple[str, str], tuple[float, StockResponse | MarketDataError]] = {}
_cache_lock = threading.Lock()
_key_locks: dict[tuple[str, str], threading.Lock] = {}


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _cache_get(key: tuple[str, str]) -> StockResponse | MarketDataError | None:
    with _cache_lock:
        item = _cache.get(key)
        if item and item[0] > time.monotonic():
            return item[1]
        _cache.pop(key, None)
        return None


def _cache_put(key: tuple[str, str], value: StockResponse | MarketDataError, ttl: float) -> None:
    with _cache_lock:
        if len(_cache) >= _MAX_CACHE_ENTRIES:
            now = time.monotonic()
            for k in [k for k, (exp, _) in _cache.items() if exp <= now] or [min(_cache, key=lambda k: _cache[k][0])]:
                _cache.pop(k, None)
        _cache[key] = (time.monotonic() + ttl, value)


def get_stock(symbol: str, period: str) -> StockResponse:
    """Return stock data for an already-validated ticker and period.

    Successful lookups and "ticker not found" results are cached briefly. Network
    failures and rate limits are never cached, and nothing is ever fabricated.
    Concurrent requests for the same key share one upstream call.
    """
    key = (symbol, period)
    cached = _cache_get(key)
    if cached is not None:
        if isinstance(cached, MarketDataError):
            raise cached
        return cached

    with _cache_lock:
        lock = _key_locks.setdefault(key, threading.Lock())
    with lock:
        cached = _cache_get(key)  # another request may have filled it while we waited
        if cached is not None:
            if isinstance(cached, MarketDataError):
                raise cached
            return cached
        try:
            df, meta = _download(symbol, period)
            result = build_stock_response(symbol, period, df, meta)
        except MarketDataError as exc:
            if isinstance(exc, TickerNotFound):
                _cache_put(key, exc, config.NEGATIVE_CACHE_TTL_SECONDS)
            raise
        except Exception as exc:  # noqa: BLE001 - never leak internals to clients
            logger.warning("Upstream failure for %s/%s: %s: %s", symbol, period, type(exc).__name__, exc)
            err = _classify(exc, symbol)
            if isinstance(err, TickerNotFound):
                _cache_put(key, err, config.NEGATIVE_CACHE_TTL_SECONDS)
            raise err from None
        _cache_put(key, result, config.CACHE_TTL_SECONDS)
        return result
