import { Wifi, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'

export function TopBar({ connected }: { connected: boolean }) {
  const [clock, setClock] = useState(new Date().toLocaleTimeString())

  useEffect(() => {
    const id = setInterval(() => setClock(new Date().toLocaleTimeString()), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="sticky top-0 z-20 border-b-2 border-accent bg-surface">
      <div className="flex items-center justify-between px-8 py-3.5">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 border border-critical/50 bg-critical/10 px-2 py-0.5">
            <span className="h-[7px] w-[7px] animate-rec-blink rounded-full bg-critical" />
            <span className="font-mono text-[10.5px] font-semibold tracking-[0.14em] text-critical">REC</span>
          </span>
          <h1 className="font-display text-[21px] font-bold uppercase tracking-[0.01em] text-ink">
            Mall Crowd Management
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <span
            className={`flex items-center gap-1.5 border px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wide ${
              connected ? 'border-good/40 bg-good/10 text-good' : 'border-warning/40 bg-warning/10 text-warning'
            }`}
          >
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {connected ? 'link ok' : 'reconnecting'}
          </span>
          <span className="font-mono text-[13px] tabular-nums text-ink-2">{clock}</span>
        </div>
      </div>
    </header>
  )
}
