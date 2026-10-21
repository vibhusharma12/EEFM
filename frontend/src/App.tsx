import { useState } from 'react'
import Navbar from './components/Navbar'
import StockOverview from './components/StockOverview'
import HistoricalChart from './components/HistoricalChart'
import PredictionPanel from './components/PredictionPanel'
import ModelPerformance from './components/ModelPerformance'
import ModelExplanation from './components/ModelExplanation'
import Footer from './components/Footer'
import { useAsyncData } from './hooks/useAsyncData'
import { stockApi } from './services/api'
import type { ForecastHorizon, HistoryRange } from './types/stock'

export default function App() {
  const [ticker, setTicker] = useState<string | null>(null)
  const [range, setRange] = useState<HistoryRange>('3M')
  const [horizon, setHorizon] = useState<ForecastHorizon>(7)
  const [request, setRequest] = useState<{ ticker: string; horizon: ForecastHorizon; n: number } | null>(null)

  // The overview always uses the shortest period (it only needs the latest sessions) so it
  // stays put while the chart reloads for a new range. The backend caches both lookups.
  const overview = useAsyncData(ticker, (signal) => stockApi.getStock(ticker as string, '1M', signal))
  const history = useAsyncData(ticker ? `${ticker}:${range}` : null, (signal) =>
    stockApi.getStock(ticker as string, range, signal),
  )

  // Predictions only run when the user clicks Predict (the counter `n` changes the key), and a
  // result is shown only for the ticker it was computed for.
  const predictionKey =
    request && request.ticker === ticker ? `${request.ticker}:${request.horizon}:${request.n}` : null
  const prediction = useAsyncData(predictionKey, (signal) =>
    stockApi.predict({ ticker: request!.ticker, horizon: request!.horizon }, signal),
  )
  const runPrediction = () => {
    if (ticker) setRequest((r) => ({ ticker, horizon, n: (r?.n ?? 0) + 1 }))
  }

  return (
    <div className="min-h-screen bg-canvas">
      <Navbar onSearch={setTicker} />
      <main id="dashboard" className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6">
        <StockOverview
          ticker={ticker}
          status={overview.status}
          stock={overview.data}
          error={overview.error}
          onRetry={overview.reload}
          onPick={setTicker}
        />
        <HistoricalChart
          ticker={ticker}
          range={range}
          onRangeChange={setRange}
          status={history.status}
          data={history.data}
          error={history.error}
          onRetry={history.reload}
        />
        <PredictionPanel
          ticker={ticker}
          horizon={horizon}
          onHorizonChange={setHorizon}
          onRun={runPrediction}
          status={prediction.status}
          data={prediction.data}
          error={prediction.error}
        />
        <ModelPerformance status={prediction.status} data={prediction.data} />
        <ModelExplanation prediction={prediction.data} />
      </main>
      <Footer />
    </div>
  )
}
