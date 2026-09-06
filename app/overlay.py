"""
Drawing helpers for the live video window: bounding boxes with track IDs
plus a summary info panel (count, FPS, status).
"""
import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX
BOX_COLOR = (0, 200, 0)
STALE_BOX_COLOR = (0, 165, 255)  # a track currently in its grace period (missed this frame)
PANEL_BG = (30, 30, 30)
TEXT_COLOR = (255, 255, 255)


def draw_tracks(frame, tracks):
    """Boxes labeled with their stable track ID."""
    for track in tracks:
        x1, y1, x2, y2 = (int(v) for v in track["box"])
        color = STALE_BOX_COLOR if track.get("is_stale") else BOX_COLOR
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"Person #{track['id']}"
        text_size = cv2.getTextSize(label, FONT, 0.5, 1)[0]
        label_y = max(y1 - 6, text_size[1] + 6)
        cv2.rectangle(frame, (x1, label_y - text_size[1] - 6), (x1 + text_size[0] + 8, label_y), color, -1)
        cv2.putText(frame, label, (x1 + 4, label_y - 4), FONT, 0.5, (0, 0, 0), 1, cv2.LINE_AA)


def draw_info_panel(frame, current_count, fps, entered=None, exited=None, status="LIVE"):
    lines = [f"PERSONS: {current_count}"]
    if entered is not None and exited is not None:
        lines.append(f"ENTERED: {entered}   EXITED: {exited}")
    lines.append(f"FPS: {fps:.1f}")
    lines.append(f"STATUS: {status}")
    panel_w = 280
    panel_h = 20 + 34 + 22 * (len(lines) - 1)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), PANEL_BG, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    y = 30
    for i, line in enumerate(lines):
        if i == 0:
            cv2.putText(frame, line, (10, y), FONT, 0.9, TEXT_COLOR, 2, cv2.LINE_AA)
            y += 34
        else:
            cv2.putText(frame, line, (10, y), FONT, 0.6, TEXT_COLOR, 1, cv2.LINE_AA)
            y += 22


def draw_offline_banner(frame):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 80), -1)
    text = "CAMERA OFFLINE"
    size = cv2.getTextSize(text, FONT, 1.2, 3)[0]
    cv2.putText(
        frame, text, ((w - size[0]) // 2, (h + size[1]) // 2),
        FONT, 1.2, (255, 255, 255), 3, cv2.LINE_AA,
    )
