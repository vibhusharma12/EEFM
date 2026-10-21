/** UI labels for the range selector. */
export type HistoryRange = '1M' | '3M' | '6M' | '1Y' | '5Y'

/** Period values understood by the backend (`?period=`). */
export type Period = '1mo' | '3mo' | '6mo' | '1y' | '5y'

export const RANGE_TO_PERIOD: Record<HistoryRange, Period> = {
  '1M': '1mo',
  '3M': '3mo',
  '6M': '6mo',
  '1Y': '1y',
  '5Y': '5y',
}

export type ForecastHorizon = 1 | 7 | 30

export interface PricePoint {
  /** ISO date (YYYY-MM-DD). */
  date: string
  close: number
}

export interface OhlcvPoint {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number
  volume: number | null
}

/** Statistics for the most recent trading session in the data. */
export interface LatestStats {
  date: string
  close: number
  previousClose: number | null
  previousDate: string | null
  change: number | null
  changePercent: number | null
  open: number | null
  dayHigh: number | null
  dayLow: number | null
  volume: number | null
}

/** Response of GET /api/stock/{ticker}?period= */
export interface StockResponse {
  ticker: string
  companyName: string | null
  exchange: string | null
  currency: string | null
  period: Period
  latest: LatestStats
  /**
   * `last_close`: the session is finished and `latest.close` is an official close.
   * `intraday_delayed`: the session is in progress; the price is the latest delayed value.
   */
  priceBasis: 'last_close' | 'intraday_delayed'
  lastTradeTime: string | null
  fetchedAt: string
  dataSource: string
  history: OhlcvPoint[]
}

export interface SearchResult {
  symbol: string
  name: string | null
  exchange: string | null
  source: 'supported_list' | 'manual'
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  note: string
}

export interface ForecastPoint {
  date: string
  predicted: number
}

/** Body of POST /api/predict. `horizon` is trading days (1-30). */
export interface PredictionRequest {
  ticker: string
  period?: Period
  horizon: number
}

export interface ClosePoint {
  date: string
  close: number
}

/** Held-out test-set metrics. `r2` can be negative, and is null when undefined. */
export interface MetricSet {
  mae: number
  rmse: number
  r2: number | null
}

export interface DateRange {
  start: string
  end: string
}

export interface FeatureImportance {
  feature: string
  importance: number
}

/** Response of POST /api/predict */
export interface PredictionResponse {
  ticker: string
  modelName: string
  generatedAt: string
  currency: string | null
  period: Period
  horizon: number
  latest: ClosePoint
  history: ClosePoint[]
  forecast: ForecastPoint[]
  predictedClose: number
  metrics: MetricSet
  baselineMetrics: MetricSet
  baselineName: string
  beatBaselineMae: boolean
  /** Positive = Random Forest has lower MAE than the baseline. */
  maeImprovementPct: number | null
  trainSamples: number
  testSamples: number
  trainPeriod: DateRange
  testPeriod: DateRange
  featureNames: string[]
  featureImportances: FeatureImportance[]
  modelReused: boolean
  trainedAt: string
  dataVersion: string
  assumptions: string[]
  limitations: string
}
