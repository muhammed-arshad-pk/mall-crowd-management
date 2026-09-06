import { Gauge, LogIn, LogOut, Users } from 'lucide-react'
import { useLiveData } from '../hooks/useLiveData'
import { CameraSourcePanel } from './CameraSourcePanel'
import { PeoplePanel } from './PeoplePanel'
import { StatCard } from './StatCard'
import { VideoPanel } from './VideoPanel'

export function LiveTab() {
  const { status } = useLiveData()

  return (
    <section className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[1.6fr_1fr]">
      <div className="flex flex-col gap-4">
        <VideoPanel cameraOk={status.camera_ok} />
        <CameraSourcePanel />
      </div>

      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Current Occupancy" value={status.current_count} icon={<Users size={13} />} />
          <StatCard label="FPS" value={status.fps.toFixed(1)} valueClassName="text-accent" icon={<Gauge size={13} />} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Entered Today" value={status.entered} valueClassName="text-good" icon={<LogIn size={13} />} />
          <StatCard label="Exited Today" value={status.exited} valueClassName="text-critical" icon={<LogOut size={13} />} />
        </div>

        <PeoplePanel people={status.people} />
      </div>
    </section>
  )
}
