import { Activity } from 'lucide-react'
import TickerSearch from './TickerSearch'

const links = [
  { href: '#dashboard', label: 'Dashboard' },
  { href: '#predictions', label: 'Predictions' },
  { href: '#about', label: 'About' },
]

export default function Navbar({ onSearch }: { onSearch: (ticker: string) => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
        <a href="#dashboard" className="flex items-center gap-2.5" aria-label="StockSense AI home">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-line-strong bg-surface text-gain">
            <Activity size={17} strokeWidth={2.4} />
          </span>
          <span className="text-[15px] font-semibold tracking-tight">
            StockSense <span className="text-muted">AI</span>
          </span>
        </a>

        <nav aria-label="Primary" className="order-3 flex w-full gap-1 sm:order-none sm:w-auto">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-md px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-ink"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto w-full sm:w-72">
          <TickerSearch onSubmit={onSearch} />
        </div>
      </div>
    </header>
  )
}
