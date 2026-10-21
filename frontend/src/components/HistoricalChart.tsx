import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ApiError } from '../services/api'
import type { HistoryRange, StockResponse } from '../types/stock'
import { formatDate, formatPercent, formatPrice } from '../lib/format'
import ChartTooltip from './ChartTooltip'
import SegmentedControl from './SegmentedControl'
import { Card, EmptyState, ErrorState, SectionHeader, Skeleton } from './ui'
import { LineChart as LineChartIcon } from 'lucide-react'

const RANGES: { value: HistoryRange; label: string }[] = [
  { value: '1M', label: '1M' },
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: '1Y', label: '1Y' },
  { value: '5Y', label: '5Y' },
]

const GAIN = '#2fcf8f'
const LOSS = '#f2555f'

interface Props {
  ticker: string | null
  range: HistoryRange
  onRangeChange: (r: HistoryRange) => void
  status: 'idle' | 'loading' | 'success' | 'error'
  data: StockResponse | null
  error: ApiError | null
  onRetry: () => void
}

export default function HistoricalChart({ ticker, range, onRangeChange, status, data, error, onRetry }: Props) {
  const points = data?.history ?? []
  const first = points[0]?.close
  const last = points[points.length - 1]?.close
  const periodChange = first && last && points.length > 1 ? ((last - first) / first) * 100 : null
  const color = periodChange !== null && periodChange < 0 ? LOSS : GAIN
  const currency = data?.currency ?? null
  const retryable = error && error.kind !== 'not_found' && error.kind !== 'invalid'

  return (
    <Card className="p-5 sm:p-6">
      <SectionHeader
        title="Price history"
        description={ticker ? `${ticker} closing price` : 'Closing price over the selected period'}
        action={
          <div className="flex items-center gap-3">
            {periodChange !== null && (
              <span className={`tabular text-sm font-medium ${periodChange < 0 ? 'text-loss' : 'text-gain'}`}>
                {formatPercent(periodChange)} <span className="text-faint">in {range}</span>
              </span>
            )}
            <SegmentedControl options={RANGES} value={range} onChange={onRangeChange} label="Date range" />
          </div>
        }
      />

      <div className="mt-5 h-72 sm:h-80">
        {status === 'idle' && (
          <EmptyState
            icon={<LineChartIcon size={18} />}
            title="Nothing to chart yet"
            description="Select a ticker to see its historical closing prices."
          />
        )}
        {status === 'loading' && <Skeleton className="h-full w-full" />}
        {status === 'error' && error && (
          <ErrorState
            title="Couldn't load price history"
            message={error.message}
            onRetry={retryable ? onRetry : undefined}
          />
        )}
        {status === 'success' && points.length === 0 && (
          <EmptyState title="No price data" description={`No history was returned for ${ticker} in this range.`} />
        )}
        {status === 'success' && points.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(d: string) => formatDate(d, range === '1Y' || range === '5Y')}
                tick={{ fill: '#5c6478', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={48}
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#5c6478', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={52}
                tickFormatter={(v: number) => v.toFixed(0)}
              />
              <Tooltip
                cursor={{ stroke: '#2b3242' }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null
                  const p = payload[0].payload as { date: string; close: number }
                  return (
                    <ChartTooltip
                      title={formatDate(p.date)}
                      rows={[{ label: 'Close', value: formatPrice(p.close, currency), color }]}
                    />
                  )
                }}
              />
              <Line
                type="monotone"
                dataKey="close"
                stroke={color}
                strokeWidth={1.75}
                dot={false}
                activeDot={{ r: 4, fill: color, stroke: '#080a0f', strokeWidth: 2 }}
                isAnimationActive
                animationDuration={500}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  )
}
