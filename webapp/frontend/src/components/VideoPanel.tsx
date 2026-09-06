export function VideoPanel({ cameraOk }: { cameraOk: boolean | null }) {
  const badgeText = cameraOk === true ? 'ONLINE' : cameraOk === false ? 'OFFLINE' : 'CONNECTING'
  const dotColor = cameraOk === true ? 'bg-good' : cameraOk === false ? 'bg-critical' : 'bg-muted'
  const textColor = cameraOk === true ? 'text-good' : cameraOk === false ? 'text-critical' : 'text-muted'

  return (
    <div className="border border-border bg-surface">
      <div className="relative aspect-video bg-black">
        <img src="/video_feed" alt="Live camera feed" className="h-full w-full object-contain" />

        <span className="frame-tick tl" />
        <span className="frame-tick tr" />
        <span className="frame-tick bl" />
        <span className="frame-tick br" />

        <div className="absolute left-4 top-4 flex items-center gap-1.5 bg-black/70 px-2 py-1 font-mono text-[11px] font-semibold tracking-wide">
          <span className={`h-[6px] w-[6px] rounded-full ${dotColor}`} />
          <span className={textColor}>CAM 01 &mdash; {badgeText}</span>
        </div>
      </div>
    </div>
  )
}
