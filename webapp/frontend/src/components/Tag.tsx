import type { LucideIcon } from 'lucide-react'

type Tone = 'good' | 'critical' | 'warning' | 'muted'

const TONE_CLASSES: Record<Tone, string> = {
  good: 'border-good/50 text-good',
  critical: 'border-critical/50 text-critical',
  warning: 'border-warning/50 text-warning',
  muted: 'border-border text-muted',
}

/** A stamped, sharp-edged tag - inspection-log vernacular, not a soft filled pill.
 * Icon + label always pair with color so state never reads from hue alone. */
export function Tag({ tone, icon: Icon, children }: { tone: Tone; icon?: LucideIcon; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 border bg-surface px-2 py-0.5 font-mono text-[10.5px] font-bold uppercase tracking-wide ${TONE_CLASSES[tone]}`}
    >
      {Icon && <Icon size={11} strokeWidth={2.5} />}
      {children}
    </span>
  )
}
