import { AlertTriangle, Radio, RefreshCw, Smartphone, Video } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { useBrowserCameraUpload } from '../hooks/useBrowserCameraUpload'
import type { CameraSource } from '../types'

export function CameraSourcePanel() {
  const [source, setSource] = useState<CameraSource | null>(null)
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const browserCam = useBrowserCameraUpload()

  const refresh = () => api.cameraSource().then(setSource).catch(() => {})

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [])

  // Release this device's camera if the user switches to a different source elsewhere.
  useEffect(() => {
    if (browserCam.active && source && source.type !== 'browser') {
      browserCam.stop()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source?.type])

  const run = async (action: () => Promise<CameraSource>, missingMsg?: string) => {
    setBusy(true)
    setFormError(null)
    try {
      setSource(await action())
    } catch (e) {
      setFormError(e instanceof Error ? e.message : missingMsg || 'Failed to switch camera source.')
    } finally {
      setBusy(false)
    }
  }

  const useWebcam = () => {
    browserCam.stop()
    run(() => api.setWebcam())
  }

  const connectPhone = () => {
    if (!url.trim()) return setFormError('Enter the URL shown by your phone’s IP camera app.')
    browserCam.stop()
    run(() => api.setIpCamera(url.trim()))
  }

  const toggleThisDeviceCamera = async () => {
    setFormError(null)
    if (browserCam.active) {
      browserCam.stop()
      run(() => api.setWebcam())
      return
    }
    await browserCam.start()
    run(() => api.setBrowserCamera())
  }

  const isWebcam = source?.type === 'webcam'
  const isPhone = source?.type === 'ip'
  const isBrowserCam = source?.type === 'browser'

  const rowButtonClass = (active: boolean) =>
    `flex shrink-0 items-center gap-1.5 border px-3 py-2 font-mono text-[12px] font-semibold uppercase tracking-wide transition-colors disabled:opacity-50 ${
      active ? 'border-accent bg-accent/10 text-accent' : 'border-border text-ink-2 hover:border-border-strong'
    }`

  return (
    <div className="border border-border bg-surface p-4">
      <h2 className="mb-3 font-display text-[13px] font-bold uppercase tracking-[0.08em] text-muted">Camera Source</h2>

      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <button onClick={useWebcam} disabled={busy} className={rowButtonClass(isWebcam) + ' flex-1 justify-center'}>
            <Radio size={13} />
            Laptop Webcam
          </button>
          <button
            onClick={toggleThisDeviceCamera}
            disabled={busy}
            className={rowButtonClass(isBrowserCam || browserCam.active) + ' flex-1 justify-center'}
          >
            <Video size={13} />
            {browserCam.active ? 'Stop This Camera' : "This Device's Camera"}
          </button>
          {browserCam.active && (
            <button
              onClick={browserCam.switchCamera}
              title={browserCam.facingMode === 'environment' ? 'Switch to front camera' : 'Switch to back camera'}
              className={rowButtonClass(false)}
            >
              <RefreshCw size={13} />
              {browserCam.facingMode === 'environment' ? 'Back' : 'Front'}
            </button>
          )}
        </div>

        <div className="flex gap-1.5">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="http://192.168.1.42:8080/video"
            className="min-w-0 flex-1 border border-border bg-ground px-2.5 py-2 font-mono text-[12px] text-ink placeholder:text-muted/70 focus:border-accent focus:outline-none"
          />
          <button onClick={connectPhone} disabled={busy} className={rowButtonClass(isPhone)}>
            <Smartphone size={13} />
            Connect
          </button>
        </div>
      </div>

      {source?.error && (
        <div className="mt-2.5 flex items-start gap-1.5 border border-critical/40 bg-critical/10 px-2.5 py-1.5 font-mono text-[11.5px] text-critical">
          <AlertTriangle size={13} className="mt-0.5 shrink-0" strokeWidth={2.5} />
          {source.error}
        </div>
      )}
      {browserCam.error && (
        <div className="mt-2.5 flex items-start gap-1.5 border border-critical/40 bg-critical/10 px-2.5 py-1.5 font-mono text-[11.5px] text-critical">
          <AlertTriangle size={13} className="mt-0.5 shrink-0" strokeWidth={2.5} />
          {browserCam.error}
        </div>
      )}
      {formError && !source?.error && !browserCam.error && (
        <div className="mt-2.5 flex items-start gap-1.5 border border-warning/40 bg-warning/10 px-2.5 py-1.5 font-mono text-[11.5px] text-warning">
          <AlertTriangle size={13} className="mt-0.5 shrink-0" strokeWidth={2.5} />
          {formError}
        </div>
      )}

      <p className="mt-2.5 font-mono text-[11px] text-muted">
        Active: <span className="text-ink-2">{source?.label ?? '—'}</span>
      </p>
    </div>
  )
}
