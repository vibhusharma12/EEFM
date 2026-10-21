import type { ReactNode } from 'react'

export interface TooltipRow {
  label: string
  value: string
  color?: string
}

/** Shared dark tooltip used by both charts. */
export default function ChartTooltip({
  title,
  rows,
  footer,
}: {
  title: string
  rows: TooltipRow[]
  footer?: ReactNode
}) {
  return (
    <div className="rounded-lg border border-line-strong bg-surface-2/95 px-3 py-2 text-xs shadow-xl backdrop-blur">
      <p className="mb-1.5 text-muted">{title}</p>
      {rows.map((r) => (
        <div key={r.label} className="flex items-center justify-between gap-6">
          <span className="flex items-center gap-1.5 text-muted">
            {r.color && <span className="h-1.5 w-1.5 rounded-full" style={{ background: r.color }} />}
            {r.label}
          </span>
          <span className="tabular font-medium text-ink">{r.value}</span>
        </div>
      ))}
      {footer}
    </div>
  )
}
