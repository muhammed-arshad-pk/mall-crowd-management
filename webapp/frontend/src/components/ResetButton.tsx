import { Check, RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'

/** Two-step confirm (click, then click "confirm" within 4s) rather than a
 * native browser confirm() dialog, to stay in the app's own visual language. */
export function ResetButton({ onReset }: { onReset: () => void }) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!confirming) return
    const id = window.setTimeout(() => setConfirming(false), 4000)
    return () => window.clearTimeout(id)
  }, [confirming])

  const handleClick = async () => {
    if (!confirming) {
      setConfirming(true)
      return
    }
    setBusy(true)
    try {
      await api.resetAll()
      onReset()
    } finally {
      setBusy(false)
      setConfirming(false)
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={busy}
      className={`flex items-center gap-1.5 border px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-wide transition-colors disabled:opacity-50 ${
        confirming
          ? 'border-critical bg-critical/15 text-critical'
          : 'border-border text-ink-2 hover:border-border-strong'
      }`}
      title="Clears all stored history and resets live counts to zero"
    >
      {confirming ? <Check size={12} /> : <RotateCcw size={12} />}
      {busy ? 'Resetting…' : confirming ? 'Click to confirm' : 'Reset All Data'}
    </button>
  )
}
