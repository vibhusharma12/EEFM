interface Option<T extends string | number> {
  value: T
  label: string
}

export default function SegmentedControl<T extends string | number>({
  options,
  value,
  onChange,
  label,
  disabled = false,
}: {
  options: Option<T>[]
  value: T
  onChange: (v: T) => void
  label: string
  disabled?: boolean
}) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="inline-flex rounded-lg border border-line bg-canvas/60 p-0.5"
    >
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={String(o.value)}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(o.value)}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
              active ? 'bg-surface-2 text-ink shadow-sm ring-1 ring-line-strong' : 'text-muted hover:text-ink'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
