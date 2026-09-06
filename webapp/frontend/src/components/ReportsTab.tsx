import { ArrowDownRight, ArrowUpRight, Gauge, LogIn, LogOut, TrendingUp, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api, fmtTime } from '../api'
import { useLiveData } from '../hooks/useLiveData'
import type { CrowdEvent, EntryExitEvent, Report } from '../types'
import { LogTable, type LogRow } from './LogTable'
import { ResetButton } from './ResetButton'
import { StatCard } from './StatCard'

function mergeByTs<T extends { ts: number }>(live: T[], historical: T[]): T[] {
  const seen = new Set(historical.map((x) => x.ts))
  const extra = live.filter((x) => !seen.has(x.ts))
  return [...extra, ...historical].slice(0, 100)
}

export function ReportsTab() {
  const { recentEntryExit, recentCrowdEvents, clearRecent } = useLiveData()
  const [report, setReport] = useState<Report | null>(null)
  const [events, setEvents] = useState<CrowdEvent[]>([])
  const [entryExit, setEntryExit] = useState<EntryExitEvent[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    Promise.all([api.report(), api.events(100), api.entryExit(100)]).then(([r, e, x]) => {
      setReport(r)
      setEvents(e)
      setEntryExit(x)
      setLoading(false)
    })
  }

  useEffect(() => {
    load()
    // The two log tables below stay live via WebSocket-pushed events (see
    // useLiveData), but the summary cards (Total Entered/Exited, Peak/Min/Avg
    // Occupancy) come from a REST snapshot - without a periodic refetch here
    // they'd freeze at whatever they were the moment this tab was opened,
    // while the tables underneath keep growing. Poll instead.
    const id = window.setInterval(load, 5000)
    return () => window.clearInterval(id)
  }, [])

  const handleReset = () => {
    clearRecent()
    load()
  }

  const mergedEvents = useMemo(() => mergeByTs(recentCrowdEvents, events), [recentCrowdEvents, events])
  const mergedEntryExit = useMemo(() => mergeByTs(recentEntryExit, entryExit), [recentEntryExit, entryExit])

  const crowdEventRows: LogRow[] = mergedEvents.map((e) => ({
    cells: [
      fmtTime(e.ts),
      String(e.previous_count),
      String(e.new_count),
      `+${e.entered}`,
      `-${e.exited}`,
      String(e.current_count),
      e.event_type,
    ],
    tagCol: 6,
    tone: e.event_type === 'EXIT' ? 'critical' : 'good',
    icon: e.event_type === 'EXIT' ? ArrowUpRight : ArrowDownRight,
  }))

  const entryExitRows: LogRow[] = mergedEntryExit.map((e) => ({
    cells: [fmtTime(e.ts), `#${e.person_id}`, e.direction],
    tagCol: 2,
    tone: e.direction === 'ENTRY' ? 'good' : 'critical',
    icon: e.direction === 'ENTRY' ? ArrowDownRight : ArrowUpRight,
  }))

  if (loading || !report) {
    return <p className="font-mono text-sm text-muted">LOADING REPORT&hellip;</p>
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-[13px] font-bold uppercase tracking-[0.08em] text-muted">Summary</h2>
        <ResetButton onReset={handleReset} />
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatCard label="Total Entered" value={report.total_entered} valueClassName="text-good" icon={<LogIn size={13} />} />
        <StatCard label="Total Exited" value={report.total_exited} valueClassName="text-critical" icon={<LogOut size={13} />} />
        <StatCard label="Currently Inside" value={report.currently_inside} valueClassName="text-accent" icon={<Users size={13} />} />
        <StatCard label="Crowd-Change Events" value={report.crowd_change_events} icon={<Gauge size={13} />} />
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-3">
        <StatCard label="Peak Occupancy" value={report.peak_occupancy} valueClassName="text-warning" icon={<TrendingUp size={13} />} />
        <StatCard label="Minimum Occupancy" value={report.min_occupancy} />
        <StatCard label="Average Occupancy" value={report.avg_occupancy} />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <LogTable
          title="Recent Crowd Events"
          columns={['Time', 'Prev', 'New', 'Entered', 'Exited', 'Current', 'Type']}
          rows={crowdEventRows}
        />
        <LogTable title="Entry / Exit Log (Line Crossing)" columns={['Time', 'Person', 'Direction']} rows={entryExitRows} />
      </div>
    </section>
  )
}
