export type TabId = 'live' | 'reports'

const TABS: { id: TabId; label: string }[] = [
  { id: 'live', label: 'Live' },
  { id: 'reports', label: 'Reports & Analysis' },
]

export function Tabs({ active, onChange }: { active: TabId; onChange: (t: TabId) => void }) {
  return (
    <nav className="sticky top-[57px] z-10 flex gap-1 border-b border-border bg-ground px-8 pt-2.5">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`border-b-2 px-4 py-2.5 font-mono text-[13px] font-semibold uppercase tracking-wide transition-colors ${
            active === t.id ? 'border-accent text-ink' : 'border-transparent text-muted hover:text-ink'
          }`}
        >
          {t.label}
        </button>
      ))}
    </nav>
  )
}
