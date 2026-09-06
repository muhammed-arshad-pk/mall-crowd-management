"""
Central configuration for the Mall Crowd Management System.

Every tunable value used across the app lives here so behavior can be
adjusted without touching detection/tracking/counting logic.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
CAMERA_SOURCE = 0          # int = local device index; a URL string = IP/RTSP camera
CAMERA_BACKEND = "dshow"   # "dshow" (fast startup on Windows) or "any"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
CAMERA_ID = "MAIN_ENTRANCE"
IP_CAMERA_TIMEOUT_MSEC = 6000  # connect/read timeout for a network camera URL

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(BASE_DIR, "models", "person_detection_model.pt")  # COCO-pretrained YOLOv8s, class 0 = person

# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.5  # 0.4 false-triggered on a hand close to the camera
IMAGE_SIZE = 640
PROCESS_EVERY_N_FRAMES = 1  # run YOLO every Nth frame (1 = every frame)
DEVICE = "auto"             # "auto", "cpu", or a CUDA device index

TRACKER_CONFIG = "bytetrack.yaml"

# ---------------------------------------------------------------------------
# Track stability
# ---------------------------------------------------------------------------
PERSON_CONFIRM_FRAMES = 3   # consecutive frames before a new track counts as a real person
TRACK_GRACE_FRAMES = 15     # consecutive missed frames tolerated before dropping a track
PERSON_DEDUP_IOU = 0.6      # overlap threshold to treat two tracks as one person (ID swap)

# ---------------------------------------------------------------------------
# Stable crowd count - separate from per-track confirmation above
# ---------------------------------------------------------------------------
COUNT_CONFIRMATION_FRAMES = 5  # consecutive frames a new count must hold before it's confirmed


def resolve_device():
    """Picks CUDA if available and DEVICE == 'auto', otherwise honors the
    explicit override in DEVICE."""
    if DEVICE != "auto":
        return DEVICE
    try:
        import torch
        return 0 if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
WINDOW_NAME = "Mall Crowd Management - Person Detection & Tracking"

# ---------------------------------------------------------------------------
# Web dashboard (run_dashboard.py)
# ---------------------------------------------------------------------------
WEB_HOST = "127.0.0.1"
WEB_PORT = 8001
DB_PATH = os.path.join(BASE_DIR, "data", "database", "crowd_management.db")
JPEG_QUALITY = 80  # quality of frames streamed to the browser (1-100)
