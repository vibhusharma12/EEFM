import { Info } from 'lucide-react'

const CURRENT_YEAR = new Date().getFullYear()

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-line">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="flex gap-3 rounded-lg border border-line bg-surface p-4">
          <Info size={16} className="mt-0.5 shrink-0 text-warn" />
          <p className="text-sm leading-relaxed text-muted">
            <span className="font-medium text-ink">Disclaimer.</span> Predictions are statistical estimates based on
            historical data and are not financial advice. Markets are unpredictable and past performance does not
            guarantee future results. Do not make investment decisions based on this tool.
          </p>
        </div>
        <p className="mt-5 text-xs text-faint">© {CURRENT_YEAR} StockSense AI · College project</p>
      </div>
    </footer>
  )
}
