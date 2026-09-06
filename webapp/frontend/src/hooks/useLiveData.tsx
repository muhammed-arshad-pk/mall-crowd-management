import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { api } from '../api'
import type { CrowdEvent, EntryExitEvent, Status, WsMessage } from '../types'

const EMPTY_STATUS: Status = {
  current_count: 0,
  entered: 0,
  exited: 0,
  people: [],
  fps: 0,
  camera_ok: null,
}

interface LiveData {
  status: Status
  connected: boolean
  recentEntryExit: EntryExitEvent[]
  recentCrowdEvents: CrowdEvent[]
  clearRecent: () => void
}

const LiveDataContext = createContext<LiveData>({
  status: EMPTY_STATUS,
  connected: false,
  recentEntryExit: [],
  recentCrowdEvents: [],
  clearRecent: () => {},
})

const MAX_LOG_ROWS = 100

export function LiveDataProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>(EMPTY_STATUS)
  const [connected, setConnected] = useState(false)
  const [recentEntryExit, setRecentEntryExit] = useState<EntryExitEvent[]>([])
  const [recentCrowdEvents, setRecentCrowdEvents] = useState<CrowdEvent[]>([])
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    // Seed once from REST so the UI isn't empty while the socket connects.
    api.status().then(setStatus).catch(() => {})

    let ws: WebSocket | null = null
    let closedByUs = false
    let retryTimer: number | null = null

    const startPolling = () => {
      if (pollRef.current !== null) return
      pollRef.current = window.setInterval(() => {
        api.status().then(setStatus).catch(() => {})
      }, 1000)
    }
    const stopPolling = () => {
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current)
        pollRef.current = null
      }
    }

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws`)

      ws.onopen = () => {
        setConnected(true)
        stopPolling()
      }
      ws.onclose = () => {
        setConnected(false)
        startPolling()
        if (!closedByUs) retryTimer = window.setTimeout(connect, 2000)
      }
      ws.onerror = () => ws?.close()
      ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data) as WsMessage
        if (data.type === 'status') {
          const { type, ...rest } = data
          setStatus(rest)
        } else if (data.type === 'entry_exit') {
          const { type, ...rest } = data
          setRecentEntryExit((prev) => [rest, ...prev].slice(0, MAX_LOG_ROWS))
        } else if (data.type === 'crowd_event') {
          const { type, ...rest } = data
          setRecentCrowdEvents((prev) => [rest, ...prev].slice(0, MAX_LOG_ROWS))
        }
      }
    }
    connect()

    return () => {
      closedByUs = true
      stopPolling()
      if (retryTimer !== null) window.clearTimeout(retryTimer)
      ws?.close()
    }
  }, [])

  const clearRecent = () => {
    setRecentEntryExit([])
    setRecentCrowdEvents([])
  }

  return (
    <LiveDataContext.Provider value={{ status, connected, recentEntryExit, recentCrowdEvents, clearRecent }}>
      {children}
    </LiveDataContext.Provider>
  )
}

export function useLiveData() {
  return useContext(LiveDataContext)
}
