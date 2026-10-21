import {
  AlertTriangle,
  BarChart3,
  Calendar,
  Compass,
  Cpu,
  Layers,
  Scale,
} from 'lucide-react'
import type { PredictionResponse } from '../types/stock'
import { Badge, Card, SectionHeader } from './ui'

interface ModelExplanationProps {
  prediction?: PredictionResponse | null
}

const TOPICS = [
  {
    icon: <Cpu size={18} className="text-accent" />,
    title: '1. What Random Forest Does',
    body: 'Random Forest Regressor fits 150 independent decision trees on bootstrap samples of the training data. Each tree predicts relative price movement; their collective average produces the final forecast, significantly curtailing single-tree variance and overfitting.',
  },
  {
    icon: <Layers size={18} className="text-accent" />,
    title: '2. Engineered Features',
    body: 'Features include relative close lags (1, 2, 3, 5, 10), daily returns, distance to Simple Moving Averages (5, 10, 20, 50 days), rolling volatility over 5, 10, and 20 sessions, intraday high-low range percentage, and volume change ratios.',
  },
  {
    icon: <Calendar size={18} className="text-accent" />,
    title: '3. Chronological Hold-out Split',
    body: 'Standard cross-validation shuffling causes target leakage in time series. We enforce a strictly chronological 80/20 split: the model is trained exclusively on earlier historical sessions and evaluated on the subsequent unseen 20% block.',
  },
  {
    icon: <Scale size={18} className="text-accent" />,
    title: '4. What MAE & RMSE Measure',
    body: 'MAE (Mean Absolute Error) measures the average dollar magnitude of forecast errors in direct price units. RMSE (Root Mean Squared Error) squares deviations before averaging, thus heavily penalizing large unexpected outlier errors.',
  },
  {
    icon: <Compass size={18} className="text-accent" />,
    title: '5. Why the Naive Baseline Matters',
    body: 'According to the efficient market hypothesis, asset prices approximate a random walk where the best unconditional prediction for tomorrow is simply today’s price. Any ML model must consistently beat this naive baseline on MAE to justify its complexity.',
  },
  {
    icon: <AlertTriangle size={18} className="text-accent" />,
    title: '6. Why Forecasting Is Inherently Hard',
    body: 'Stock markets have low signal-to-noise ratios, non-stationary distributions, and regime changes. Price movements are driven by unexpected news, earnings releases, and geopolitical shifts that cannot be anticipated from historical price tables alone.',
  },
]

export default function ModelExplanation({ prediction = null }: ModelExplanationProps) {
  const importances = prediction?.featureImportances?.slice(0, 8) ?? []

  return (
    <Card id="about" className="p-5 sm:p-6">
      <SectionHeader
        title="Model methodology & scientific principles"
        description="Comprehensive breakdown of our machine learning pipeline, feature engineering, and evaluation rigor."
        action={
          prediction ? (
            <Badge tone="accent">Trained on {prediction.ticker}</Badge>
          ) : (
            <Badge tone="neutral">Standard Architecture</Badge>
          )
        }
      />

      {/* Explanatory Grid */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {TOPICS.map((topic) => (
          <div
            key={topic.title}
            className="flex flex-col rounded-lg border border-line bg-canvas/40 p-4 transition-colors hover:border-line-strong"
          >
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-md border border-line-strong bg-surface-2">
                {topic.icon}
              </span>
              <h3 className="text-sm font-semibold text-ink">{topic.title}</h3>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted">{topic.body}</p>
          </div>
        ))}
      </div>

      {/* Feature Importance Section */}
      {importances.length > 0 && (
        <div className="mt-6 rounded-lg border border-line bg-canvas/30 p-4">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 size={16} className="text-accent" />
              <h3 className="text-sm font-semibold text-ink">
                Random Forest Feature Importances ({prediction?.ticker})
              </h3>
            </div>
            <span className="text-[11px] text-faint">
              Mean impurity decrease across 150 estimators
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {importances.map((item) => {
              const pct = (item.importance * 100).toFixed(1)
              return (
                <div key={item.feature} className="flex flex-col gap-1 text-xs">
                  <div className="flex items-center justify-between text-muted">
                    <span className="font-mono text-[11px] text-ink">{item.feature}</span>
                    <span className="font-mono">{pct}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-surface-2 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent transition-all duration-500"
                      style={{ width: `${Math.max(Number(pct), 2)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          <p className="mt-3 text-[11px] leading-relaxed text-faint">
            <strong className="text-ink">Note on Causation:</strong> Feature importance measures
            the frequency and impurity reduction with which a feature was selected to split decision
            trees. It demonstrates empirical predictive correlation within this sample,{' '}
            <em>not financial causation</em>.
          </p>
        </div>
      )}

      {/* Mandatory Disclaimer */}
      <div className="mt-6 rounded-lg border border-line-strong bg-surface-2/40 p-4 text-xs leading-relaxed text-muted">
        <p className="font-medium text-ink">Disclaimer</p>
        <p className="mt-0.5">
          Forecasts are generated by a statistical model using historical market data. They are
          estimates, not guarantees, and should not be treated as financial advice.
        </p>
      </div>
    </Card>
  )
}
