import type { ReactNode } from 'react'
import { AlertTriangle, RefreshCw, SearchX } from 'lucide-react'

export function Card({
  children,
  className = '',
  id,
}: {
  children: ReactNode
  className?: string
  id?: string
}) {
  return (
    <section
      id={id}
      className={`rounded-xl border border-line bg-surface transition-colors duration-200 hover:border-line-strong ${className}`}
    >
      {children}
    </section>
  )
}

export function SectionHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-base font-semibold tracking-tight text-ink">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

type BadgeTone = 'neutral' | 'warn' | 'accent'

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: BadgeTone }) {
  const tones: Record<BadgeTone, string> = {
    neutral: 'border-line-strong bg-surface-2 text-muted',
    warn: 'border-warn/30 bg-warn/10 text-warn',
    accent: 'border-accent/30 bg-accent/10 text-accent',
  }
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />
}

export function EmptyState({
  title,
  description,
  children,
  icon,
}: {
  title: string
  description: string
  children?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-line-strong bg-surface-2 text-muted">
        {icon ?? <SearchX size={18} />}
      </div>
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted">{description}</p>
      {children && <div className="mt-4">{children}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'Unable to load data',
  message,
  onRetry,
}: {
  title?: string
  message: string
  onRetry?: () => void
}) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-loss/30 bg-loss/10 text-loss">
        <AlertTriangle size={18} />
      </div>
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-md text-sm text-muted">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface-2 px-3 py-1.5 text-sm text-ink transition-colors hover:border-accent/50 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
        >
          <RefreshCw size={14} /> Try again
        </button>
      )}
    </div>
  )
}
