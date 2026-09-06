export interface Person {
  id: number
  is_stale: boolean
}

export interface Status {
  current_count: number
  entered: number
  exited: number
  people: Person[]
  fps: number
  camera_ok: boolean | null
}

export interface EntryExitEvent {
  ts: number
  person_id: number
  direction: 'ENTRY' | 'EXIT'
  camera_id?: string
}

export interface CrowdEvent {
  ts: number
  previous_count: number
  new_count: number
  entered: number
  exited: number
  current_count: number
  event_type: 'INITIAL' | 'ENTRY' | 'EXIT' | 'COUNT_CHANGE'
}

export interface CameraSource {
  type: 'webcam' | 'ip' | 'file' | 'browser'
  value: string | null
  label: string
  error: string | null
}

export interface Report {
  total_entered: number
  total_exited: number
  currently_inside: number
  peak_occupancy: number
  min_occupancy: number
  avg_occupancy: number
  crowd_change_events: number
}

export type WsMessage =
  | ({ type: 'status' } & Status)
  | ({ type: 'entry_exit' } & { person_id: number; direction: 'ENTRY' | 'EXIT'; ts: number })
  | ({ type: 'crowd_event' } & {
      previous_count: number
      new_count: number
      entered: number
      exited: number
      current_count: number
      event_type: CrowdEvent['event_type']
      ts: number
    })
