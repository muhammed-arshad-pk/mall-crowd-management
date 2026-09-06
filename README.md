# Mall Crowd Management & People Counting System

Real-time person detection, tracking, and crowd counting from a live camera
feed, with a stable occupancy count, an SQLite event log, and a browser
dashboard.

```
Camera → YOLOv8 person detection → ByteTrack
       → track confirmation / grace period
       → stable aggregate count      → crowd_events (SQLite)
       → frame-based entry/exit      → entry_exit_events (SQLite)
       → live overlay → (dashboard) WebSocket → browser UI
```

## Status

| Stage | | |
|---|---|---|
| 1 | Camera → YOLO person detection → live count | ✅ |
| 2 | Person tracking (ByteTrack) + stable-count debounce | ✅ |
| 3 | Count-change event register (`crowd_events`) in SQLite | ✅ |
| 4 | Frame-based entry/exit (person appears/disappears) | ✅ |
| 5 | Browser dashboard, IP/RTSP camera, phone-camera support | ✅ |
| 6 | Historical graph, CSV/Excel export, occupancy alerts | ⏳ planned |

## Two ways to run it

- **`app/main.py`** — local OpenCV window.
- **`run_dashboard.py`** — full browser dashboard: live video, live stats, camera switching, and a Reports tab (event register, entry/exit log). Shareable over the network (e.g. Cloudflare Tunnel).

Both share the same pipeline (`app/crowd_engine.py`).

## Two counting concepts

- **Current Occupancy** — the confirmed aggregate count (`counting.CountStabilizer`). A row is written to `crowd_events` only when this changes, never per frame.
- **Entry / Exit Events** — a specific tracked person appeared (`ENTRY`) or disappeared (`EXIT`) from view. This is what backs the cumulative Entered/Exited totals — a raw count delta alone can't prove a physical entry/exit.

The camera's field of view is the entry/exit boundary itself (e.g. mounted at a doorway) — no virtual line to configure.

## Tech stack

YOLOv8 (Ultralytics) + ByteTrack · OpenCV · FastAPI + Uvicorn + WebSockets · SQLite · React 19 + TypeScript + Vite · Tailwind CSS v4

## Project structure

```
mall_crowd_management/
├── app/
│   ├── main.py         # OpenCV-window entrypoint
│   ├── config.py       # every tunable constant
│   ├── camera.py       # camera source abstraction (webcam/IP/RTSP/file)
│   ├── detector.py     # PersonDetector (YOLO, class 0 only)
│   ├── tracker.py      # PersonTracker (grace-period + dedup + confirm-frames)
│   ├── counting.py     # CountStabilizer
│   ├── crowd_engine.py # shared detect/track/count/entry-exit pipeline
│   └── overlay.py      # OpenCV window drawing
│
├── webapp/
│   ├── server.py        # FastAPI: capture thread, REST API, WebSocket, MJPEG
│   ├── database.py      # SQLite storage + summary report
│   ├── frontend/        # React + TypeScript source (edit here)
│   └── static/          # build output - already built and committed
│
├── run_dashboard.py
├── models/person_detection_model.pt   # COCO-pretrained YOLOv8s
├── data/{database, daily_records, exports}/
├── logs/
├── snapshots/
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+ / npm — only needed to modify the dashboard frontend
- A webcam, IP/RTSP camera, or phone (browser-camera option)

## Installation

```bash
git clone <this-repo-url>
cd mall_crowd_management

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

No further setup — the model is included in `models/`, and the dashboard's frontend is pre-built in `webapp/static/`.

Verify:
```bash
python -c "import ultralytics, cv2, fastapi; print('OK')"
```

## Running it

**OpenCV window:**
```bash
python app/main.py
```
Press **Q** to quit.

**Browser dashboard:**
```bash
python run_dashboard.py
```
Open **http://127.0.0.1:8001**.

Don't run both at once — only one process can hold the camera at a time.

### Camera options (switchable at runtime, from the dashboard)

- **Webcam** — default.
- **IP / RTSP camera** — enter the stream URL.
- **"This Device's Camera"** — the device viewing the dashboard streams its own camera via the browser (`getUserMedia`) — useful for a phone with no IP-camera app. Requires HTTPS or `localhost`.

### Sharing over the network

```bash
# Terminal 1
python run_dashboard.py
# Terminal 2
cloudflared tunnel --url http://127.0.0.1:8001
```

## Configuration (`app/config.py`)

| Setting | Meaning |
|---|---|
| `CAMERA_SOURCE` | `0` = default webcam. Also switchable at runtime. |
| `MODEL_PATH` | COCO-pretrained YOLOv8s — class 0 = person. |
| `CONFIDENCE_THRESHOLD` | Minimum detection confidence (`0.5`). |
| `PERSON_CONFIRM_FRAMES` | Consecutive frames before a new track counts as a person (`3`). |
| `TRACK_GRACE_FRAMES` | Missed frames tolerated before dropping a track (`15`). |
| `PERSON_DEDUP_IOU` | Overlap threshold to merge two tracks into one person (`0.6`). |
| `COUNT_CONFIRMATION_FRAMES` | Consecutive frames before a count change is confirmed (`5`). |
| `IMAGE_SIZE`, `PROCESS_EVERY_N_FRAMES`, `DEVICE` | Inference resolution, frame-skip, GPU/CPU. |
| `WEB_HOST` / `WEB_PORT` | Dashboard bind address (`127.0.0.1:8001`). |

## Database

SQLite (`data/database/crowd_management.db`), two tables:

- **`crowd_events`** — one row per confirmed count change: `timestamp`, `date`, `previous_count`, `new_count`, `entered`, `exited`, `current_count`, `event_type` (`INITIAL`/`ENTRY`/`EXIT`), `camera_id`.
- **`entry_exit_events`** — one row per tracked person appearing/disappearing: `timestamp`, `person_id`, `direction` (`ENTRY`/`EXIT`), `camera_id`.

## Dashboard API

| Endpoint | Purpose |
|---|---|
| `GET /` | Dashboard page |
| `GET /video_feed` | MJPEG live video |
| `WS /ws` | Live status + event push |
| `GET /api/status` | Current snapshot |
| `GET /api/events` | Recent `crowd_events` |
| `GET /api/entry_exit` | Recent `entry_exit_events` |
| `GET /api/report` | Summary totals |
| `GET/POST /api/camera` | Read/switch camera source |
| `POST /api/reset` | Wipe history, restart camera |
| `WS /ws/camera_upload` | Phone camera frame upload |

## Modifying the dashboard frontend

```bash
cd webapp/frontend
npm install
npm run dev     # hot-reload dev server
npm run build   # rebuilds webapp/static/ - commit it too
```

## Limitations / roadmap

- No historical graph, CSV export, or capacity alerts yet (Stage 6).
- Single camera only — DB schema already carries `camera_id` for future multi-camera support.
- No face/identity recognition by design — anonymous tracking IDs only.

## Troubleshooting

- **Can't access the webcam** — check it's not open in another app, check OS camera permissions, try a different `CAMERA_SOURCE`.
- **False detections (e.g. a hand)** — raise `CONFIDENCE_THRESHOLD` / `PERSON_CONFIRM_FRAMES`.
- **Same person double-counted after a brief occlusion** — raise `TRACK_GRACE_FRAMES`.
- **"This Device's Camera" won't start** — needs HTTPS or `localhost`.
