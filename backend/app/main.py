import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import config, market
from .ml.errors import MLError
from .routes import predictions
from .schemas import ErrorResponse, HealthResponse, SearchResponse, SearchResult, StockResponse
from .symbols import SUPPORTED_SYMBOLS, normalize_ticker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("stocksense")

app = FastAPI(title="StockSense AI API", version=config.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)


@app.exception_handler(market.MarketDataError)
async def market_error_handler(_: Request, exc: market.MarketDataError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(MLError)
async def ml_error_handler(_: Request, exc: MLError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError | ValidationError) -> JSONResponse:
    errors = exc.errors()
    details = []
    for err in errors:
        loc = ".".join(str(l) for l in err.get("loc", []) if l != "body")
        msg = err.get("msg", "invalid value")
        details.append(f"{loc}: {msg}" if loc else msg)
    message = f"Invalid request parameters: {'; '.join(details)}" if details else "Invalid request parameters."
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Full details go to the server log only; clients get a generic message.
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=config.APP_VERSION, time=datetime.now(timezone.utc).isoformat())


@app.get(
    "/api/stock/{ticker}",
    response_model=StockResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["stocks"],
)
def get_stock(ticker: str, period: str = Query("6mo")) -> StockResponse:
    """Latest available session statistics and daily OHLCV history for a ticker."""
    symbol = normalize_ticker(ticker)
    if symbol is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker symbol. Use letters, numbers, '.' or '-' (for example AAPL or RELIANCE.NS).",
        )
    period = period.strip().lower()
    if period not in market.ALLOWED_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Supported periods: {', '.join(market.ALLOWED_PERIODS)}.",
        )
    return market.get_stock(symbol, period)


@app.get("/api/search", response_model=SearchResponse, tags=["stocks"])
def search(q: str = Query("", max_length=40)) -> SearchResponse:
    """Suggest symbols from a small built-in list; valid manual tickers can be queried directly."""
    query = q.strip()
    note = (
        "Suggestions come from a small built-in list, not a full company search. "
        "Any valid Yahoo Finance ticker can be entered directly."
    )
    if not query:
        results = [SearchResult(**s, source="supported_list") for s in SUPPORTED_SYMBOLS]
        return SearchResponse(query=query, results=results, note=note)

    needle = query.lower()
    matches = [
        s for s in SUPPORTED_SYMBOLS if s["symbol"].lower().startswith(needle) or needle in s["name"].lower()
    ]
    # Symbol-prefix matches first.
    matches.sort(key=lambda s: not s["symbol"].lower().startswith(needle))
    results = [SearchResult(**s, source="supported_list") for s in matches]

    manual = normalize_ticker(query)
    if manual and all(r.symbol != manual for r in results):
        results.append(SearchResult(symbol=manual, name=None, exchange=None, source="manual"))
    return SearchResponse(query=query, results=results, note=note)
