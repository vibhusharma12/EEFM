"""Small curated symbol list used for suggestions.

This is NOT a full company search. Any other valid ticker can still be looked up
directly by typing it; Yahoo Finance decides whether it exists.
"""
import re

TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-^=]{0,14}$")

SUPPORTED_SYMBOLS: list[dict[str, str]] = [
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "name": "Tesla, Inc.", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Class A)", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "name": "Amazon.com, Inc.", "exchange": "NASDAQ"},
    {"symbol": "META", "name": "Meta Platforms, Inc.", "exchange": "NASDAQ"},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited", "exchange": "NSE"},
    {"symbol": "INFY.NS", "name": "Infosys Limited", "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE"},
]


def normalize_ticker(raw: str) -> str | None:
    """Return the upper-cased ticker if it is syntactically valid, else None."""
    t = raw.strip().upper()
    return t if TICKER_PATTERN.match(t) else None
