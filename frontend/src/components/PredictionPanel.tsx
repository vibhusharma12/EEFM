import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertCircle, BrainCircuit, CheckCircle2, Play, Sparkles, XCircle } from 'lucide-react'
import type { ApiError } from '../services/api'
import type { ForecastHorizon, PredictionResponse } from '../types/stock'
import { formatDate, formatPercent, formatPrice, formatSigned, trendClass } from '../lib/format'
import ChartTooltip from './ChartTooltip'
import SegmentedControl from './SegmentedControl'
import { Badge, Card, SectionHeader } from './ui'

const HORIZONS: { value: ForecastHorizon; label: string }[] = [
  { value: 1, label: '1 day' },
  { value: 7, label: '7 days' },
  { value: 30, label: '30 days' },
]

interface ChartRow {
  x: string
  actual?: number
  predicted?: number
}

interface PredictionPanelProps {
  ticker: string | null
  horizon: ForecastHorizon
  onHorizonChange: (horizon: ForecastHorizon) => void
  onRun: () => void
  status: 'idle' | 'loading' | 'success' | 'error'
  data: PredictionResponse | null
  error: ApiError | null
}

export default function PredictionPanel({
  ticker,
  horizon,
  onHorizonChange,
  onRun,
  status,
  data,
  error,
}: PredictionPanelProps) {
  const live = status === 'success' && data !== null && data.ticker === ticker
  const currency = data?.currency ?? 'USD'

  let rows: ChartRow[] = []
  let boundary = 'Today'

  if (live && data) {
    const hist = data.history.slice(-60)
    rows = hist.map((p) => ({ x: p.date, actual: p.close }))
    if (rows.length > 0) {
      boundary = rows[rows.length - 1].x
      rows[rows.length - 1].predicted = rows[rows.length - 1].actual
    }
    data.forecast.forEach((f) => rows.push({ x: f.date, predicted: f.predicted }))
  }

  const expectedChange =
    live && data ? data.predictedClose - data.latest.close : null
  const expectedChangePct =
    live && data && data.latest.close > 0
      ? (expectedChange! / data.latest.close) * 100
      : null

  return (
    <Card id="predictions" className="p-5 sm:p-6">
      <SectionHeader
        title="Stock price forecasting"
        description="Recursive Random Forest forecasts alongside recent historical closing prices."
        action={
          <div className="flex flex-wrap items-center gap-3">
            <SegmentedControl
              options={HORIZONS}
              value={horizon}
              onChange={onHorizonChange}
              label="Forecast horizon"
            />
            <button
              type="button"
              onClick={onRun}
              disabled={!ticker || status === 'loading'}
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-canvas shadow-sm transition-all hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Play size={13} fill="currentColor" />
              {status === 'loading' ? 'Training & predicting…' : 'Run forecast'}
            </button>
          </div>
        }
      />

      {/* Status Badges */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {live && data ? (
          <>
            <Badge tone="accent">{data.modelName}</Badge>
            <span className="text-xs text-muted">
              {data.horizon}-session recursive horizon for{' '}
              <strong className="text-ink">{data.ticker}</strong>
            </span>
            <Badge tone={data.modelReused ? 'neutral' : 'accent'}>
              {data.modelReused ? 'Model cached' : 'Newly trained'}
            </Badge>
          </>
        ) : (
          <span className="text-xs text-faint">
            {ticker
              ? `Ready to train model for ${ticker}. Select a horizon and click "Run forecast".`
              : 'Select a ticker above to run the predictive model.'}
          </span>
        )}
      </div>

      {/* Error alert */}
      {status === 'error' && error && (
        <div
          role="alert"
          className="mt-4 flex items-start gap-3 rounded-lg border border-loss/30 bg-loss/10 p-4 text-sm text-loss"
        >
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Prediction failed</p>
            <p className="mt-0.5 leading-relaxed text-loss/90">{error.message}</p>
          </div>
        </div>
      )}

      {/* Highlight stats when prediction is live */}
      {live && data && (
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-line bg-canvas/40 p-4">
            <span className="text-xs text-faint">Latest observed close</span>
            <p className="mt-1 font-mono text-xl font-semibold text-ink">
              {formatPrice(data.latest.close, currency)}
            </p>
            <p className="mt-0.5 text-xs text-muted">Session {data.latest.date}</p>
          </div>

          <div className="rounded-lg border border-line bg-canvas/40 p-4">
            <span className="text-xs text-faint">Predicted target close (T+{data.horizon})</span>
            <p className="mt-1 font-mono text-xl font-semibold text-accent">
              {formatPrice(data.predictedClose, currency)}
            </p>
            <p className="mt-0.5 flex items-center gap-1 text-xs">
              <span className={`font-medium ${trendClass(expectedChange)}`}>
                {formatSigned(expectedChange)} ({formatPercent(expectedChangePct)})
              </span>
              <span className="text-muted">by {data.forecast[data.forecast.length - 1]?.date}</span>
            </p>
          </div>

          <div className="rounded-lg border border-line bg-canvas/40 p-4">
            <span className="text-xs text-faint">Hold-out test performance</span>
            <div className="mt-1 flex items-center gap-1.5 font-mono text-xl font-semibold text-ink">
              {data.beatBaselineMae ? (
                <>
                  <CheckCircle2 size={18} className="text-gain" />
                  <span className="text-gain">Beat baseline</span>
                </>
              ) : (
                <>
                  <XCircle size={18} className="text-warn" />
                  <span className="text-warn">Trailing baseline</span>
                </>
              )}
            </div>
            <p className="mt-0.5 text-xs text-muted">
              RF MAE {formatPrice(data.metrics.mae, currency)} vs Naive{' '}
              {formatPrice(data.baselineMetrics.mae, currency)}
            </p>
          </div>
        </div>
      )}

      {/* Main Chart Area */}
      <div className="relative mt-5 h-72 sm:h-80">
        {status === 'loading' ? (
          <div className="flex h-full w-full flex-col items-center justify-center rounded-lg border border-line bg-surface-2/40 p-6 text-center">
            <BrainCircuit size={32} className="animate-pulse text-accent" />
            <p className="mt-3 text-sm font-semibold text-ink">
              Training Random Forest & computing forecast…
            </p>
            <p className="mt-1 max-w-sm text-xs text-muted">
              Fitting 150 decision trees on chronological history and running recursive step-ahead
              projections.
            </p>
          </div>
        ) : live ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="#1f2430" />
              <XAxis
                dataKey="x"
                tickFormatter={(v: string) => formatDate(v, false)}
                tick={{ fill: '#5c6478', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={40}
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#5c6478', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={56}
                tickFormatter={(v: number) => v.toFixed(0)}
              />
              <ReferenceLine
                x={boundary}
                stroke="#6f93f5"
                strokeDasharray="3 3"
                label={{
                  value: 'Forecast start',
                  position: 'insideTopLeft',
                  fill: '#6f93f5',
                  fontSize: 10,
                }}
              />
              <Tooltip
                cursor={{ stroke: '#2b3242' }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const p = payload[0].payload as ChartRow
                  const fmt = (v: number) => formatPrice(v, currency)
                  const tooltipRows = []
                  if (p.actual !== undefined)
                    tooltipRows.push({ label: 'Actual Close', value: fmt(p.actual), color: '#e7eaf1' })
                  if (p.predicted !== undefined && p.x !== boundary)
                    tooltipRows.push({
                      label: 'Predicted Close',
                      value: fmt(p.predicted),
                      color: '#6f93f5',
                    })
                  if (!tooltipRows.length) return null
                  return <ChartTooltip title={formatDate(p.x)} rows={tooltipRows} />
                }}
              />
              <Line
                type="monotone"
                dataKey="actual"
                name="Historical Actual"
                stroke="#e7eaf1"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="predicted"
                name="Forecast"
                stroke="#6f93f5"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={{ r: 2.5, fill: '#6f93f5' }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center rounded-lg border border-dashed border-line bg-canvas/30 p-6 text-center">
            <Sparkles size={28} className="text-muted" />
            <p className="mt-3 text-sm font-medium text-ink">No forecast generated yet</p>
            <p className="mt-1 max-w-sm text-xs text-muted">
              Select a horizon ({HORIZONS.map((h) => h.label).join(', ')}) and click{' '}
              <span className="font-semibold text-ink">"Run forecast"</span> to train the Random Forest
              on historical price data.
            </p>
          </div>
        )}
      </div>

      {/* Legend & Disclaimer */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-4 border-t border-line/60 pt-4 text-xs text-muted">
        <div className="flex items-center gap-5">
          <span className="flex items-center gap-2">
            <span className="h-0.5 w-5 rounded bg-ink" /> Historical Actual
          </span>
          <span className="flex items-center gap-2">
            <span className="h-0.5 w-5 rounded border-t-2 border-dashed border-accent" /> ML Forecast (T+1 to T+{horizon})
          </span>
        </div>

        <div className="flex items-center gap-2 text-faint">
          <span>Skips weekends</span>
          <span>·</span>
          <span>Assumes recent avg volatility</span>
        </div>
      </div>

      {/* Mandatory Disclaimer */}
      <div className="mt-4 rounded-lg border border-line-strong bg-surface-2/40 p-3 text-xs leading-relaxed text-muted">
        <span className="font-medium text-ink">Disclaimer:</span> Forecasts are generated by a
        statistical model using historical market data. They are estimates, not guarantees, and
        should not be treated as financial advice.
      </div>
    </Card>
  )
}
