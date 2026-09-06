"""
Camera interface. Supports three source kinds:
  - "webcam": a local device index (int), e.g. 0.
  - "ip": a network camera URL (str), e.g. "rtsp://192.168.1.50:554/stream".
  - "file": a local video file path (str), for testing against a clip.
"""
import cv2

import config


def open_camera(source=None, kind=None):
    """source: None (use config.CAMERA_SOURCE), an int device index, or a
    URL/file-path string. kind: "webcam" | "ip" | "file"; inferred from the
    source's type if not given (int -> webcam, str -> ip)."""
    src = config.CAMERA_SOURCE if source is None else source
    if kind is None:
        kind = "webcam" if isinstance(src, int) else "ip"

    if kind == "webcam":
        backend = cv2.CAP_DSHOW if config.CAMERA_BACKEND == "dshow" else cv2.CAP_ANY
        cap = cv2.VideoCapture(src, backend)
    elif kind == "ip":
        # A wrong/unreachable camera URL should fail fast (few seconds), not
        # hang on FFmpeg's much longer default TCP connect timeout - these
        # must be passed at construction time, .set() afterward is too late.
        cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, config.IP_CAMERA_TIMEOUT_MSEC,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, config.IP_CAMERA_TIMEOUT_MSEC,
        ])
    else:  # "file"
        cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        return None

    if kind == "webcam":
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    return cap
