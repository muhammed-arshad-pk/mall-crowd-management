import type { CameraSource, CrowdEvent, EntryExitEvent, Report, Status } from './types'

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  return res.json() as Promise<T>
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || `${url} -> ${res.status}`)
  return data as T
}

export const api = {
  status: () => getJson<Status>('/api/status'),
  events: (limit = 100) => getJson<CrowdEvent[]>(`/api/events?limit=${limit}`),
  entryExit: (limit = 100) => getJson<EntryExitEvent[]>(`/api/entry_exit?limit=${limit}`),
  report: () => getJson<Report>('/api/report'),
  cameraSource: () => getJson<CameraSource>('/api/camera'),
  setWebcam: () => postJson<CameraSource>('/api/camera', { type: 'webcam' }),
  setIpCamera: (url: string) => postJson<CameraSource>('/api/camera', { type: 'ip', url }),
  setVideoFile: (path: string) => postJson<CameraSource>('/api/camera', { type: 'file', path }),
  setBrowserCamera: () => postJson<CameraSource>('/api/camera', { type: 'browser' }),
  resetAll: () => postJson<{ ok: boolean }>('/api/reset', {}),
}

export function fmtTime(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleTimeString()
}

export function fmtDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}
