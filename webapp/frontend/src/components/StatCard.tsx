import type { ReactNode } from 'react'

export function StatCard({
  label,
  value,
  valueClassName = '',
  icon,
}: {
  label: string
  value: ReactNode
  valueClassName?: string
  icon?: ReactNode
}) {
  return (
    <div className="border border-border bg-surface p-4">
      <div className="mb-2 flex items-center gap-1.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.1em] text-muted">
        {icon}
        {label}
      </div>
      {/* Hero figures stay in the body sans, never the display face - per mark spec. */}
      <div className={`font-sans text-[27px] font-semibold leading-none ${valueClassName}`}>{value}</div>
    </div>
  )
}
