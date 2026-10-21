import { HelpCircle } from 'lucide-react'
import type { PredictionResponse } from '../types/stock'
import { formatDateTime, formatPrice } from '../lib/format'
import { Badge, Card, SectionHeader, Skeleton } from './ui'

function MetricCard({
  label,
  hint,
  value,
  loading,
  detail,
  tone = 'default',
}: {
  label: string
  hint: string
  value: string | null
  loading: boolean
  detail?: string
  tone?: 'default' | 'gain' | 'warn' | 'accent'
}) {
  const toneClasses = {
    default: 'text-ink',
    gain: 'text-gain',
    warn: 'text-warn',
    accent: 'text-accent',
  }

  return (
    <div className="flex flex-col justify-between rounded-lg border border-line bg-canvas/40 p-4 transition-colors hover:border-line-strong">
      <div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-ink">{label}</span>
          {value === null && !loading && <Badge>Pending run</Badge>}
        </div>
        <p className="mt-0.5 text-xs text-faint">{hint}</p>
      </div>

      <div className="mt-4 min-h-8">
        {loading ? (
          <Skeleton className="h-7 w-24" />
        ) : value !== null ? (
          <p className={`tabular font-mono text-2xl font-semibold tracking-tight ${toneClasses[tone]}`}>
            {value}
          </p>
        ) : (
          <p className="text-2xl font-semibold text-line-strong">—</p>
        )}
      </div>

      {detail && <p className="mt-2 text-xs text-muted leading-relaxed">{detail}</p>}
    </div>
  )
}

interface ModelPerformanceProps {
  status?: 'idle' | 'loading' | 'success' | 'error'
  data?: PredictionResponse | null
}

export default function ModelPerformance({ status = 'idle', data = null }: ModelPerformanceProps) {
  const loading = status === 'loading'
  const m = data?.metrics
  const b = data?.baselineMetrics
  const currency = data?.currency ?? 'USD'

  const maeImp = data?.maeImprovementPct ?? null
  const beat = data?.beatBaselineMae

  return (
    <Card className="p-5 sm:p-6">
      <SectionHeader
        title="Model evaluation & baseline comparison"
        description="Rigorous chronological hold-out evaluation on unseen future sessions (never training data)."
        action={
          data ? (
            <div className="flex items-center gap-2">
              <Badge tone="accent">Evaluated {formatDateTime(data.trainedAt)}</Badge>
              <Badge tone={beat ? 'accent' : 'warn'}>
                {beat ? 'Random Forest wins on MAE' : 'Baseline wins on MAE'}
              </Badge>
            </div>
          ) : (
            <Badge>No evaluation loaded</Badge>
          )
        }
      />

      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Test MAE"
          hint="Mean Absolute Error on test set"
          loading={loading}
          value={m ? formatPrice(m.mae, currency) : null}
          detail={b ? `Naive baseline MAE: ${formatPrice(b.mae, currency)}` : undefined}
          tone={beat ? 'gain' : 'default'}
        />

        <MetricCard
          label="Test RMSE"
          hint="Root Mean Squared Error"
          loading={loading}
          value={m ? formatPrice(m.rmse, currency) : null}
          detail={b ? `Naive baseline RMSE: ${formatPrice(b.rmse, currency)}` : undefined}
        />

        <MetricCard
          label="Test R²"
          hint="Variance explained vs mean"
          loading={loading}
          // Explicitly display negative R² correctly without clamping to zero!
          value={m ? (m.r2 !== null ? m.r2.toFixed(3) : 'Undefined (constant target)') : null}
          detail={
            m?.r2 !== null && m?.r2 !== undefined
              ? m.r2 < 0
                ? 'Negative R² indicates predicting the historical mean would have yielded lower error.'
                : 'Proportion of test variance accounted for by the model.'
              : undefined
          }
          tone={m?.r2 !== null && m?.r2 !== undefined && m.r2 < 0 ? 'warn' : 'default'}
        />

        <MetricCard
          label="vs. Naive Baseline"
          hint="Hurdle: tomorrow's close = today's close"
          loading={loading}
          value={
            maeImp !== null
              ? `${maeImp > 0 ? '+' : ''}${maeImp.toFixed(2)}%`
              : null
          }
          tone={beat ? 'gain' : 'warn'}
          detail={
            data
              ? beat
                ? 'Random Forest outperformed naive persistence on MAE.'
                : 'Honest evaluation: naive baseline had a lower MAE on this test split.'
              : undefined
          }
        />
      </div>

      {/* Dataset & Window transparency */}
      {data && (
        <div className="mt-5 grid grid-cols-1 gap-3 rounded-lg border border-line bg-canvas/30 p-4 sm:grid-cols-2 text-xs">
          <div>
            <span className="font-semibold text-ink">Chronological Train Set:</span>{' '}
            <span className="text-muted">{data.trainSamples} trading days</span>
            <p className="mt-0.5 text-faint">
              Window: {data.trainPeriod.start} to {data.trainPeriod.end}
            </p>
          </div>
          <div>
            <span className="font-semibold text-ink">Held-Out Test Set (20%):</span>{' '}
            <span className="text-muted">{data.testSamples} trading days</span>
            <p className="mt-0.5 text-faint">
              Window: {data.testPeriod.start} to {data.testPeriod.end}
            </p>
          </div>
        </div>
      )}

      {!data && !loading && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-line bg-surface-2/30 p-3 text-xs text-muted">
          <HelpCircle size={15} className="text-muted shrink-0" />
          <span>
            Evaluation metrics will populate as soon as you run a prediction for a stock. Metrics
            are calculated exclusively on the held-out test block so they reflect true out-of-sample
            performance.
          </span>
        </div>
      )}
    </Card>
  )
}
