import { UserCheck, UserX } from 'lucide-react'
import type { Person } from '../types'
import { Tag } from './Tag'

export function PeoplePanel({ people }: { people: Person[] }) {
  return (
    <div className="border border-border bg-surface p-5">
      <h2 className="mb-3.5 font-display text-[13px] font-bold uppercase tracking-[0.08em] text-muted">People In View</h2>
      {people.length === 0 ? (
        <p className="text-sm text-muted">No one in frame yet.</p>
      ) : (
        <div className="flex max-h-[420px] flex-col gap-2 overflow-y-auto">
          {people.map((p) => (
            <div
              key={p.id}
              className={`flex items-center justify-between border-l-[3px] bg-surface-raised p-3 ${
                p.is_stale ? 'border-l-warning' : 'border-l-good'
              }`}
            >
              <span className="font-sans font-semibold">Person #{p.id}</span>
              <Tag tone={p.is_stale ? 'warning' : 'good'} icon={p.is_stale ? UserX : UserCheck}>
                {p.is_stale ? 'HOLDING' : 'TRACKED'}
              </Tag>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
