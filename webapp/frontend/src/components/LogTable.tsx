import { Camera } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Tag } from './Tag'

export interface LogRow {
  cells: string[]
  tagCol: number
  tone: 'good' | 'critical'
  icon: LucideIcon
  snapshotUrl?: string | null
}

export function LogTable({
  title,
  columns,
  rows,
  onViewSnapshot,
}: {
  title: string
  columns: string[]
  rows: LogRow[]
  onViewSnapshot?: (url: string) => void
}) {
  const hasSnapshotCol = Boolean(onViewSnapshot)

  return (
    <div className="border border-border bg-surface p-5">
      <h2 className="mb-3.5 font-display text-[13px] font-bold uppercase tracking-[0.08em] text-muted">{title}</h2>
      <div className="max-h-[320px] overflow-y-auto">
        <table className="w-full border-collapse font-mono text-[12.5px]">
          <thead>
            <tr>
              {columns.map((c) => (
                <th
                  key={c}
                  className="sticky top-0 border-b border-border bg-surface px-2 py-2 text-left text-[10.5px] font-bold uppercase tracking-wide text-muted"
                >
                  {c}
                </th>
              ))}
              {hasSnapshotCol && (
                <th className="sticky top-0 border-b border-border bg-surface px-2 py-2 text-left text-[10.5px] font-bold uppercase tracking-wide text-muted">
                  Snapshot
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (hasSnapshotCol ? 1 : 0)} className="py-3 text-muted">
                  No entries yet.
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr key={i} className={i % 2 === 1 ? 'bg-surface-raised/50' : ''}>
                  {row.cells.map((cell, j) => (
                    <td key={j} className="px-2 py-1.5 tabular-nums text-ink-2">
                      {j === row.tagCol ? (
                        <Tag tone={row.tone} icon={row.icon}>
                          {cell}
                        </Tag>
                      ) : (
                        cell
                      )}
                    </td>
                  ))}
                  {hasSnapshotCol && (
                    <td className="px-2 py-1.5">
                      {row.snapshotUrl ? (
                        <button
                          onClick={() => onViewSnapshot?.(row.snapshotUrl as string)}
                          className="flex items-center gap-1 border border-border px-2 py-0.5 text-[11px] uppercase tracking-wide text-accent hover:border-accent"
                        >
                          <Camera size={11} />
                          View
                        </button>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
