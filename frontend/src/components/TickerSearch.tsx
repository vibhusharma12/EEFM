import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Search } from 'lucide-react'
import { stockApi } from '../services/api'
import type { SearchResult } from '../types/stock'

const TICKER_PATTERN = /^[A-Z0-9][A-Z0-9.\-^=]{0,14}$/

function normalizeTicker(raw: string): string | null {
  const t = raw.trim().toUpperCase()
  return TICKER_PATTERN.test(t) ? t : null
}

export default function TickerSearch({
  onSubmit,
  id = 'ticker-search',
}: {
  onSubmit: (ticker: string) => void
  id?: string
}) {
  const [value, setValue] = useState('')
  const [invalid, setInvalid] = useState(false)
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<SearchResult[]>([])
  const [active, setActive] = useState(-1)
  const wrapRef = useRef<HTMLDivElement>(null)
  const listId = useId()

  // Debounced suggestions from the backend's supported-symbol list. If the backend is
  // unreachable, suggestions simply don't appear; typing a ticker still works.
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      stockApi
        .search(value.trim(), controller.signal)
        .then((res) => {
          setResults(res.results.slice(0, 8))
          setActive(-1)
        })
        .catch(() => {
          if (!controller.signal.aborted) setResults([])
        })
    }, 180)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [value, open])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const choose = (symbol: string) => {
    setValue('')
    setOpen(false)
    setInvalid(false)
    onSubmit(symbol)
  }

  const handle = (e: FormEvent) => {
    e.preventDefault()
    if (active >= 0 && results[active]) return choose(results[active].symbol)
    const t = normalizeTicker(value)
    if (!t) {
      setInvalid(true)
      return
    }
    choose(t)
  }

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive((a) => Math.min(a + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, -1))
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const showList = open && results.length > 0

  return (
    <div ref={wrapRef} className="relative w-full">
      <form onSubmit={handle} role="search" noValidate>
        <label htmlFor={id} className="sr-only">
          Search stock ticker
        </label>
        <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
        <input
          id={id}
          value={value}
          onChange={(e) => {
            setValue(e.target.value.toUpperCase())
            setOpen(true)
            if (invalid) setInvalid(false)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search ticker, e.g. AAPL"
          autoComplete="off"
          spellCheck={false}
          maxLength={15}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-invalid={invalid}
          className={`w-full rounded-lg border bg-surface-2 py-2 pl-9 pr-12 font-mono text-sm uppercase text-ink placeholder:font-sans placeholder:normal-case placeholder:text-faint transition-colors focus:outline-none ${
            invalid ? 'border-loss/60' : 'border-line focus:border-accent/60'
          }`}
        />
        <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line-strong px-1.5 py-0.5 text-[10px] text-faint sm:block">
          Enter
        </kbd>
      </form>

      {invalid && (
        <p role="alert" className="absolute left-0 top-full mt-1 text-xs text-loss">
          Enter a valid ticker (letters/numbers, '.' or '-', up to 15 characters).
        </p>
      )}

      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute left-0 right-0 top-full z-40 mt-1.5 overflow-hidden rounded-lg border border-line-strong bg-surface shadow-2xl"
        >
          {results.map((r, i) => (
            <li
              key={r.symbol}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault()
                choose(r.symbol)
              }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm ${
                i === active ? 'bg-surface-2' : ''
              }`}
            >
              <span className="font-mono text-ink">{r.symbol}</span>
              <span className="truncate text-xs text-muted">
                {r.source === 'manual' ? 'Look up this ticker' : `${r.name ?? ''}${r.exchange ? ` · ${r.exchange}` : ''}`}
              </span>
            </li>
          ))}
          <li className="border-t border-line px-3 py-1.5 text-[11px] text-faint" aria-hidden="true">
            Short built-in list; any valid Yahoo Finance ticker works.
          </li>
        </ul>
      )}
    </div>
  )
}
