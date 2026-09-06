"""
Camera -> YOLO person detection -> ByteTrack -> track confirmation/grace
period -> stable aggregate count -> frame-based entry/exit, shown in a
plain OpenCV window.

For the browser dashboard (live video + history + reports) instead of this
OpenCV window, run `python run_dashboard.py` from the project root - see
README.md. Don't run both at once; a webcam can only be opened by one
process at a time.

Run with: python app/main.py
Press Q in the video window to quit.
"""
import logging
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import overlay
from camera import open_camera
from crowd_engine import CrowdEngine

os.makedirs(os.path.join(config.BASE_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(config.BASE_DIR, "logs", "app.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_READ_FAILURES = 30
RECONNECT_RETRY_DELAY_SEC = 2


def main():
    logger.info("Application started")

    cap = open_camera()
    if cap is None:
        print(
            "ERROR: could not access the camera (source={}).\n"
            "  - Check it's connected and not already in use by another app.\n"
            "  - Check Windows camera privacy permissions for this app/terminal.\n"
            "  - Try a different CAMERA_SOURCE in config.py (0, 1, 2...).".format(
                config.CAMERA_SOURCE
            )
        )
        logger.error("Could not access camera at startup (source=%s)", config.CAMERA_SOURCE)
        return
    logger.info("Camera connected (source=%s)", config.CAMERA_SOURCE)

    device = config.resolve_device()
    logger.info("Using device: %s", device)
    engine = CrowdEngine(device=device)
    logger.info("Model loaded: %s", config.MODEL_PATH)

    cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)

    frame_idx = 0
    consecutive_failures = 0
    camera_offline = False
    result = None
    fps = 0.0
    prev_time = time.time()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                consecutive_failures += 1
                if not camera_offline:
                    logger.warning("Frame grab failed (%d/%d)", consecutive_failures, MAX_CONSECUTIVE_READ_FAILURES)
                if consecutive_failures >= MAX_CONSECUTIVE_READ_FAILURES and not camera_offline:
                    camera_offline = True
                    logger.error("Camera disconnected - attempting reconnection")
                if camera_offline:
                    offline_frame = frame_offline_placeholder()
                    overlay.draw_offline_banner(offline_frame)
                    cv2.imshow(config.WINDOW_NAME, offline_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    time.sleep(RECONNECT_RETRY_DELAY_SEC)
                    cap.release()
                    cap = open_camera()
                    if cap is not None:
                        logger.info("Camera reconnected")
                        camera_offline = False
                        consecutive_failures = 0
                continue

            if camera_offline:
                logger.info("Camera recovered")
            camera_offline = False
            consecutive_failures = 0

            run_inference = frame_idx % config.PROCESS_EVERY_N_FRAMES == 0
            if run_inference:
                result = engine.infer(frame)
                if result.stable_count_change is not None:
                    previous, new = result.stable_count_change
                    logger.info("Stable count changed: %d -> %d", previous, new)
                for track_id, event in result.entry_exit_events:
                    logger.info("Person %sED (ID %d) - Entered: %d Exited: %d",
                                event, track_id, result.entered, result.exited)

            if result is not None:
                engine.draw(frame, result)

                now = time.time()
                dt = now - prev_time
                prev_time = now
                if dt > 0:
                    instant_fps = 1.0 / dt
                    fps = instant_fps if fps == 0 else fps * 0.9 + instant_fps * 0.1

                overlay.draw_info_panel(frame, result.current_count, fps, result.entered, result.exited)

            cv2.imshow(config.WINDOW_NAME, frame)
            frame_idx += 1

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Application stopped")


def frame_offline_placeholder():
    import numpy as np
    return np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype="uint8")


if __name__ == "__main__":
    main()
