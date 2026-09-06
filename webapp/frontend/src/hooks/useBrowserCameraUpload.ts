import { useCallback, useRef, useState } from 'react'

const UPLOAD_INTERVAL_MS = 150 // ~6-7 fps upload - plenty for a monitoring feed, keeps bandwidth low

type FacingMode = 'user' | 'environment'

/** Captures this device's own camera via getUserMedia and streams JPEG
 * frames to the server over a WebSocket, for use as the "This Device's
 * Camera" source. Requires a secure context (HTTPS or localhost) - a hard
 * browser rule for camera access, not something this code can work around. */
export function useBrowserCameraUpload() {
  const [active, setActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [facingMode, setFacingMode] = useState<FacingMode>('environment')
  const streamRef = useRef<MediaStream | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const intervalRef = useRef<number | null>(null)

  const stop = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    wsRef.current?.close()
    wsRef.current = null
    setActive(false)
  }, [])

  const openStream = useCallback(async (mode: FacingMode) => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: mode, width: { ideal: 960 }, height: { ideal: 540 } },
      audio: false,
    })
    streamRef.current = stream
    if (!videoRef.current) {
      const video = document.createElement('video')
      video.muted = true
      video.playsInline = true
      videoRef.current = video
    }
    videoRef.current.srcObject = stream
    await videoRef.current.play()
  }, [])

  const start = useCallback(
    async (mode: FacingMode = facingMode) => {
      setError(null)

      if (!window.isSecureContext) {
        setError('Camera access needs HTTPS (or localhost). Open this page via a secure URL.')
        return
      }
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('This browser does not support camera access.')
        return
      }

      try {
        setFacingMode(mode)
        await openStream(mode)
        canvasRef.current = document.createElement('canvas')

        const proto = location.protocol === 'https:' ? 'wss' : 'ws'
        const ws = new WebSocket(`${proto}://${location.host}/ws/camera_upload`)
        ws.binaryType = 'arraybuffer'
        wsRef.current = ws

        ws.onopen = () => {
          setActive(true)
          intervalRef.current = window.setInterval(() => {
            const v = videoRef.current
            const c = canvasRef.current
            if (!v || !c || v.videoWidth === 0 || wsRef.current?.readyState !== WebSocket.OPEN) return
            c.width = v.videoWidth
            c.height = v.videoHeight
            const ctx = c.getContext('2d')
            if (!ctx) return
            ctx.drawImage(v, 0, 0)
            c.toBlob(
              (blob) => {
                if (blob && wsRef.current?.readyState === WebSocket.OPEN) {
                  blob.arrayBuffer().then((buf) => wsRef.current?.send(buf))
                }
              },
              'image/jpeg',
              0.7,
            )
          }, UPLOAD_INTERVAL_MS)
        }
        ws.onclose = () => setActive(false)
        ws.onerror = () => setError('Lost connection to the server while streaming the camera.')
      } catch (e) {
        if (e instanceof DOMException && e.name === 'NotAllowedError') {
          setError('Camera permission denied. Allow camera access and try again.')
        } else if (e instanceof DOMException && e.name === 'NotFoundError') {
          setError('No camera found on this device.')
        } else {
          setError(e instanceof Error ? e.message : 'Failed to access the camera.')
        }
        stop()
      }
    },
    [facingMode, openStream, stop],
  )

  /** Swaps front <-> back camera without dropping the WebSocket/upload loop -
   * just replaces the video track feeding the capture canvas. */
  const switchCamera = useCallback(async () => {
    if (!active) return
    const nextMode: FacingMode = facingMode === 'environment' ? 'user' : 'environment'
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      setFacingMode(nextMode)
      await openStream(nextMode)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to switch camera.')
    }
  }, [active, facingMode, openStream])

  return { active, error, facingMode, start, stop, switchCamera }
}
