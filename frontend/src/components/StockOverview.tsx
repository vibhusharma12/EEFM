import { TrendingDown, TrendingUp } from 'lucide-react'
import type { StockResponse } from '../types/stock'
import {
  formatDateTime,
  formatPercent,
  formatPrice,
  formatSigned,
  formatTradingDate,
  formatVolume,
  trendClass,
} from '../lib/format'
import { Badge, Card, EmptyState, ErrorState, Skeleton } from './ui'
import type { ApiError } from '../services/api'

interface Props {
  ticker: string | null
  status: 'idle' | 'loading' | 'success' | 'error'
  stock: StockResponse | null
  error: ApiError | null
  onRetry: () => void
  onPick: (ticker: string) => void
}

const SUGGESTIONS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'RELIANCE.NS', 'TCS.NS', 'INFY.NS']

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-line bg-canvas/40 px-3.5 py-3 transition-colors hover:border-line-strong">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="tabular mt-1 text-[15px] font-medium text-ink">{value}</dd>
      {sub && <p className="mt-0.5 text-[11px] text-faint">{sub}</p>}
    </div>
  )
}

export default function StockOverview({ ticker, status, stock, error, onRetry, onPick }: Props) {
  return (
    <Card className="p-5 sm:p-6">
      {status === 'idle' && (
        <EmptyState
          title="No stock selected"
          description="Search for a ticker symbol in the navigation bar, or pick one below. Indian stocks use the .NS suffix (e.g. RELIANCE.NS)."
        >
          <div className="flex flex-wrap justify-center gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onPick(s)}
                className="rounded-md border border-line-strong bg-surface-2 px-2.5 py-1 font-mono text-xs text-ink transition-colors hover:border-accent/50 hover:text-accent"
              >
                {s}
              </button>
            ))}
          </div>
        </EmptyState>
      )}

      {status === 'loading' && (
        <div aria-busy="true" aria-label="Loading stock overview">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="mt-4 h-10 w-56" />
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        </div>
      )}

      {status === 'error' && error && (
        <ErrorState
          title={
            error.kind === 'not_found' || error.kind === 'invalid'
              ? `Can't load ${ticker}`
              : 'Unable to load stock data'
          }
          message={error.message}
          onRetry={error.kind === 'not_found' || error.kind === 'invalid' ? undefined : onRetry}
        />
      )}

      {status === 'success' && stock && (
        <div className="animate-fade-up">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h2 className="max-w-xl break-words text-lg font-semibold tracking-tight text-ink">
                  {stock.companyName ?? stock.ticker}
                </h2>
                <span className="rounded-md border border-line-strong bg-surface-2 px-2 py-0.5 font-mono text-xs text-muted">
                  {stock.ticker}
                </span>
                {stock.exchange && <span className="text-xs text-faint">{stock.exchange}</span>}
              </div>
              <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span className="tabular text-4xl font-semibold tracking-tight">
                  {formatPrice(stock.latest.close, stock.currency)}
                </span>
                <span
                  className={`tabular inline-flex items-center gap-1.5 text-base font-medium ${trendClass(stock.latest.change)}`}
                >
                  {stock.latest.change !== null &&
                    (stock.latest.change < 0 ? <TrendingDown size={16} /> : <TrendingUp size={16} />)}
                  {formatSigned(stock.latest.change)} ({formatPercent(stock.latest.changePercent)})
                </span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                {stock.priceBasis === 'last_close' ? (
                  <Badge>Latest close · not live</Badge>
                ) : (
                  <Badge tone="warn">Session in progress · delayed</Badge>
                )}
                <span className="text-xs text-faint">
                  {stock.priceBasis === 'last_close' ? 'Session of' : 'Trading day'}{' '}
                  {formatTradingDate(stock.latest.date)}
                </span>
              </div>
            </div>
            <div className="text-xs leading-relaxed text-faint sm:text-right">
              {stock.lastTradeTime && <p>Last trade {formatDateTime(stock.lastTradeTime)}</p>}
              <p>Retrieved {formatDateTime(stock.fetchedAt)}</p>
              <p>Source: {stock.dataSource}</p>
            </div>
          </div>

          <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat
              label="Previous close"
              value={formatPrice(stock.latest.previousClose, stock.currency)}
              sub={stock.latest.previousDate ? formatTradingDate(stock.latest.previousDate) : undefined}
            />
            <Stat label="Day high" value={formatPrice(stock.latest.dayHigh, stock.currency)} />
            <Stat label="Day low" value={formatPrice(stock.latest.dayLow, stock.currency)} />
            <Stat label="Volume" value={formatVolume(stock.latest.volume)} />
          </dl>
        </div>
      )}
    </Card>
  )
}
