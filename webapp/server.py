"""
FastAPI web dashboard: live MJPEG video, live stats over WebSocket, and a
history/reports API backed by SQLite.

The camera + detection pipeline runs in a single background thread, owned
by CameraManager. The active source (webcam, IP/RTSP camera, or "This
Device's Camera") can be switched at runtime via POST /api/camera; switching
starts a fresh CrowdEngine, so tracking state doesn't carry over.

Run with: python run_dashboard.py (from the project root).
"""
import asyncio
import json
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))

import config
from camera import open_camera
from crowd_engine import CrowdEngine
from webapp import database

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

EMPTY_STATUS = {
    "current_count": 0, "entered": 0, "exited": 0,
    "people": [], "fps": 0.0, "camera_ok": None,
}


class Broadcaster:
    """Thread-safe bridge between the background (non-async) capture thread
    and the asyncio event loop serving WebSocket clients."""

    def __init__(self):
        self.loop = None
        self._clients = set()

    def bind_loop(self, loop):
        self.loop = loop

    def add_client(self, ws):
        self._clients.add(ws)

    def remove_client(self, ws):
        self._clients.discard(ws)

    def publish_threadsafe(self, message):
        """Call from the background capture thread (not a coroutine)."""
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self.loop)

    async def _broadcast(self, message):
        if not self._clients:
            return
        data = json.dumps(message)
        dead = []
        for ws in list(self._clients):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)


class SharedState:
    """Latest frame + status snapshot, guarded by a lock. Written by the
    background capture thread, read by HTTP/WebSocket handlers."""

    def __init__(self):
        self.lock = threading.Lock()
        self.jpeg_bytes = None
        self.status = dict(EMPTY_STATUS)

    def set_frame(self, jpeg_bytes):
        with self.lock:
            self.jpeg_bytes = jpeg_bytes

    def get_frame(self):
        with self.lock:
            return self.jpeg_bytes

    def set_status(self, status):
        with self.lock:
            self.status = status

    def get_status(self):
        with self.lock:
            return dict(self.status)

    def reset(self):
        with self.lock:
            self.jpeg_bytes = None
            self.status = dict(EMPTY_STATUS)


class IncomingFrameBuffer:
    """Holds the latest frame uploaded by a browser acting as the camera
    (see /ws/camera_upload). The capture loop polls get_new() instead of
    calling cap.read() when source_type == "browser"."""

    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self._seq = 0
        self._consumed_seq = 0
        self._last_received = 0.0

    def push(self, frame):
        with self._lock:
            self._frame = frame
            self._seq += 1
            self._last_received = time.time()

    def get_new(self):
        with self._lock:
            if self._seq == self._consumed_seq:
                return None
            self._consumed_seq = self._seq
            return self._frame

    def seconds_since_last(self):
        with self._lock:
            return None if self._last_received == 0.0 else time.time() - self._last_received

    def reset(self):
        with self._lock:
            self._frame = None
            self._seq = 0
            self._consumed_seq = 0
            self._last_received = 0.0


broadcaster = Broadcaster()
shared = SharedState()
incoming_frame_buffer = IncomingFrameBuffer()


class CameraManager:
    """Owns the single background capture thread and lets it be stopped and
    restarted against a different source (webcam <-> IP camera <-> this
    device's camera) from an HTTP request, without restarting the whole
    server."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self.source_type = "webcam"    # "webcam" | "ip" | "file" | "browser"
        self.source_value = config.CAMERA_SOURCE
        self.label = "Laptop Webcam"
        self.error = None

    def info(self):
        with self._lock:
            return {
                "type": self.source_type,
                "value": None if self.source_type == "webcam" else self.source_value,
                "label": self.label,
                "error": self.error,
            }

    def start_default(self):
        self._start("webcam", config.CAMERA_SOURCE, "Laptop Webcam")

    def switch(self, source_type, value):
        if source_type == "webcam":
            self._start("webcam", config.CAMERA_SOURCE, "Laptop Webcam")
        elif source_type == "file":
            name = Path(value).name
            self._start("file", value, f"Video File ({name})")
        elif source_type == "browser":
            self._start("browser", None, "This Device's Camera")
        else:
            self._start("ip", value, f"IP Camera ({value})")

    def restart(self):
        """Reopens the current source fresh - a new CrowdEngine means a
        clean slate (current count back to 0, entered/exited back to 0,
        tracker state cleared). Used by the "reset everything" action."""
        with self._lock:
            source_type, value, label = self.source_type, self.source_value, self.label
        self._start(source_type, value, label)

    def _start(self, source_type, value, label):
        with self._lock:
            self._stop_locked()
            self.source_type = source_type
            self.source_value = value
            self.label = label
            self.error = None
            shared.reset()
            self._stop_event = threading.Event()
            stop_event = self._stop_event
            self._thread = threading.Thread(
                target=self._run, args=(stop_event, source_type, value), daemon=True
            )
            self._thread.start()

    def stop(self):
        with self._lock:
            self._stop_locked()

    def _stop_locked(self):
        if self._thread is not None and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=5)
        self._thread = None

    def _run(self, stop_event, source_type, value):
        cap = None
        if source_type == "browser":
            incoming_frame_buffer.reset()
        else:
            cap = open_camera(None if source_type == "webcam" else value, kind=source_type)
            if cap is None:
                if source_type == "webcam":
                    message = "Could not open the webcam. Is it connected, and not in use by another app?"
                elif source_type == "file":
                    message = f"Could not open video file: {value}. Check the path is correct and readable."
                else:
                    message = (
                        f"Could not open IP camera at {value}. Check the camera is reachable on the "
                        f"network and the URL is correct."
                    )
                logger.error(message)
                with self._lock:
                    self.error = message
                shared.set_status({**EMPTY_STATUS, "camera_ok": False})
                return

        engine = CrowdEngine()
        first_event_logged = False

        frame_idx = 0
        result = None
        fps = 0.0
        prev_time = time.time()
        consecutive_failures = 0

        try:
            while not stop_event.is_set():
                if source_type == "browser":
                    frame = incoming_frame_buffer.get_new()
                    if frame is None:
                        idle = incoming_frame_buffer.seconds_since_last()
                        if idle is not None and idle > 15:
                            with self._lock:
                                self.error = (
                                    "No frames received in 15s - is the browser tab still open "
                                    "with the camera active?"
                                )
                            shared.set_status({**shared.get_status(), "camera_ok": False})
                        time.sleep(0.05)
                        continue
                else:
                    ok, frame = cap.read()
                    if not ok:
                        if source_type == "file":
                            # End of the clip - loop back to the start so a short
                            # test video keeps playing instead of stopping.
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                        consecutive_failures += 1
                        if consecutive_failures >= 30:
                            logger.error("Too many consecutive frame failures; stopping capture.")
                            with self._lock:
                                self.error = "Lost the video stream (too many failed reads in a row)."
                            shared.set_status({**shared.get_status(), "camera_ok": False})
                            break
                        continue
                    consecutive_failures = 0

                run_inference = result is None or frame_idx % config.PROCESS_EVERY_N_FRAMES == 0
                if run_inference:
                    result = engine.infer(frame)

                    if result.stable_count_change is not None:
                        previous, new = result.stable_count_change
                        event_type = "INITIAL" if not first_event_logged else ("ENTRY" if new > previous else "EXIT")
                        first_event_logged = True
                        database.log_crowd_event(previous, new, event_type)
                        broadcaster.publish_threadsafe({
                            "type": "crowd_event", "previous_count": previous, "new_count": new,
                            "entered": max(0, new - previous), "exited": max(0, previous - new),
                            "current_count": new, "event_type": event_type, "ts": time.time(),
                        })

                    for track_id, event in result.entry_exit_events:
                        direction = "ENTRY" if event == "ENTER" else "EXIT"
                        database.log_entry_exit(track_id, direction)
                        broadcaster.publish_threadsafe({
                            "type": "entry_exit", "person_id": track_id, "direction": direction, "ts": time.time(),
                        })

                    engine.draw(frame, result)

                now = time.time()
                dt = now - prev_time
                prev_time = now
                if dt > 0:
                    instant_fps = 1.0 / dt
                    fps = instant_fps if fps == 0 else fps * 0.9 + instant_fps * 0.1

                ok_enc, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY])
                if ok_enc:
                    shared.set_frame(buf.tobytes())

                status = {
                    "current_count": result.current_count,
                    "entered": result.entered,
                    "exited": result.exited,
                    "people": [{"id": t["id"], "is_stale": t["is_stale"]} for t in result.active_tracks],
                    "fps": round(fps, 1),
                    "camera_ok": True,
                }
                shared.set_status(status)
                broadcaster.publish_threadsafe({"type": "status", **status})

                frame_idx += 1
        finally:
            if cap is not None:
                cap.release()


camera_manager = CameraManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    database.init_db()
    broadcaster.bind_loop(asyncio.get_event_loop())
    camera_manager.start_default()
    yield
    camera_manager.stop()


app = FastAPI(title="Mall Crowd Management", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


def _mjpeg_generator():
    boundary = b"--frame"
    while True:
        frame = shared.get_frame()
        if frame is None:
            time.sleep(0.05)
            continue
        yield boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        time.sleep(1 / 30)


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(_mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/status")
def api_status():
    return JSONResponse(shared.get_status())


@app.get("/api/events")
def api_events(limit: int = 50):
    return JSONResponse(database.recent_crowd_events(limit))


@app.get("/api/entry_exit")
def api_entry_exit(limit: int = 50):
    return JSONResponse(database.recent_entry_exit_events(limit))


@app.get("/api/report")
def api_report():
    return JSONResponse(database.summary_report())


@app.post("/api/reset")
def api_reset():
    """Clears all stored history and restarts the current camera source with
    a fresh CrowdEngine, so occupancy counts and tracking state also start
    at zero - a full "start everything fresh" for e.g. before a live demo."""
    database.reset_all()
    camera_manager.restart()
    return JSONResponse({"ok": True})


class CameraSourceRequest(BaseModel):
    type: str  # "webcam" | "ip" | "file" | "browser"
    url: str | None = None
    path: str | None = None


@app.get("/api/camera")
def api_camera_get():
    return JSONResponse(camera_manager.info())


@app.post("/api/camera")
def api_camera_set(body: CameraSourceRequest):
    if body.type not in ("webcam", "ip", "file", "browser"):
        return JSONResponse({"error": "type must be 'webcam', 'ip', 'file', or 'browser'"}, status_code=400)

    if body.type == "ip":
        url = (body.url or "").strip()
        if not url:
            return JSONResponse({"error": "url is required for type 'ip'"}, status_code=400)
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("rtsp://")):
            return JSONResponse(
                {"error": "url must start with http://, https://, or rtsp://"}, status_code=400
            )
        camera_manager.switch("ip", url)
    elif body.type == "file":
        path = (body.path or "").strip()
        if not path:
            return JSONResponse({"error": "path is required for type 'file'"}, status_code=400)
        if not Path(path).is_file():
            return JSONResponse({"error": f"File not found: {path}"}, status_code=400)
        camera_manager.switch("file", path)
    elif body.type == "browser":
        camera_manager.switch("browser", None)
    else:
        camera_manager.switch("webcam", None)

    return JSONResponse(camera_manager.info())


@app.websocket("/ws/camera_upload")
async def ws_camera_upload(websocket: WebSocket):
    """Receives binary JPEG frames from a browser acting as the camera (see
    the "This Device's Camera" option) and feeds them into the capture loop
    via incoming_frame_buffer. Frames are ignored (not an error - the client
    may just be mid-switch) unless the camera source is currently "browser"."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
            if camera_manager.info()["type"] != "browser":
                continue
            arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None:
                incoming_frame_buffer.push(frame)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    broadcaster.add_client(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "status", **shared.get_status()}))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        broadcaster.remove_client(websocket)
