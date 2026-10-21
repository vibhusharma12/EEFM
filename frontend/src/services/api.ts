import axios, { AxiosError } from 'axios'
import type { HistoryRange, PredictionRequest, PredictionResponse, SearchResponse, StockResponse } from '../types/stock'
import { RANGE_TO_PERIOD } from '../types/stock'

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  (import.meta.env.PROD ? '' : 'http://localhost:8000')

const client = axios.create({
  baseURL: API_BASE_URL,
  // Slightly above the backend's upstream timeout so the backend can report its own error first.
  timeout: 25000,
})

export type ApiErrorKind = 'network' | 'invalid' | 'not_found' | 'rate_limit' | 'upstream' | 'server' | 'unknown'

export class ApiError extends Error {
  kind: ApiErrorKind
  status?: number

  constructor(message: string, kind: ApiErrorKind, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err
  if (axios.isCancel(err)) return new ApiError('Request cancelled', 'unknown')
  if (err instanceof AxiosError) {
    if (!err.response) {
      if (err.code === 'ECONNABORTED') {
        return new ApiError('The request timed out. Please try again.', 'network')
      }
      return new ApiError(
        `Cannot reach the StockSense API at ${API_BASE_URL}. Make sure the backend is running.`,
        'network',
      )
    }
    const status = err.response.status
    const raw = (err.response.data as { detail?: unknown } | undefined)?.detail
    const detail = typeof raw === 'string' ? raw : undefined
    if (status === 400 || status === 422) return new ApiError(detail ?? 'Invalid request.', 'invalid', status)
    if (status === 404) return new ApiError(detail ?? 'Ticker not found.', 'not_found', status)
    if (status === 429) return new ApiError(detail ?? 'Too many requests. Please wait and retry.', 'rate_limit', status)
    if (status === 502 || status === 503 || status === 504) {
      return new ApiError(detail ?? 'The market data provider is unavailable.', 'upstream', status)
    }
    if (status >= 500) return new ApiError(detail ?? 'The server ran into a problem.', 'server', status)
    return new ApiError(detail ?? `Request failed (${status}).`, 'unknown', status)
  }
  return new ApiError('Something went wrong.', 'unknown')
}

async function get<T>(url: string, params?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  try {
    const res = await client.get<T>(url, { params, signal })
    return res.data
  } catch (err) {
    throw toApiError(err)
  }
}

export const stockApi = {
  /** GET /api/stock/{ticker}?period= : latest session stats + OHLCV history. */
  getStock: (ticker: string, range: HistoryRange, signal?: AbortSignal) =>
    get<StockResponse>(
      `/api/stock/${encodeURIComponent(ticker)}`,
      { period: RANGE_TO_PERIOD[range] },
      signal,
    ),

  /** GET /api/search?q= : suggestions from the backend's supported-symbol list. */
  search: (q: string, signal?: AbortSignal) => get<SearchResponse>('/api/search', { q }, signal),

  /**
   * POST /api/predict : trains (or reuses) the Random Forest and returns the forecast plus
   * held-out evaluation. The first request for a ticker trains a model, so allow extra time.
   */
  predict: async (req: PredictionRequest, signal?: AbortSignal): Promise<PredictionResponse> => {
    try {
      const res = await client.post<PredictionResponse>('/api/predict', req, { signal, timeout: 90000 })
      return res.data
    } catch (err) {
      throw toApiError(err)
    }
  },
}
