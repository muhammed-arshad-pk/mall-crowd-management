"""
Tracking layer on top of PersonDetector's ByteTrack IDs. Adds:

  1. New-track confirmation - a new ID must be seen for PERSON_CONFIRM_FRAMES
     consecutive frames before it counts as a real person (filters brief
     false positives).
  2. A grace period so a confirmed track survives a few missed frames
     (motion blur, brief occlusion) without dropping the count.
  3. Overlap dedup - if occlusion makes ByteTrack swap a person to a new ID,
     two heavily-overlapping tracks are collapsed into one.
"""
import config


def _iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    intersection = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


class PersonTracker:
    """Wraps PersonDetector and debounces brief per-frame detection failures."""

    def __init__(self, person_detector, grace_frames=config.TRACK_GRACE_FRAMES,
                 dedup_iou=config.PERSON_DEDUP_IOU, confirm_frames=config.PERSON_CONFIRM_FRAMES):
        self.detector = person_detector
        self.grace_frames = grace_frames
        self.dedup_iou = dedup_iou
        self.confirm_frames = confirm_frames
        self._tracks = {}  # track_id -> {"box": (x1,y1,x2,y2), "conf": float, "missed": int}
        self._pending = {}  # track_id -> {"box", "conf", "streak"} - not yet confirmed as a real person

    def update(self, frame):
        """Runs detection+tracking on one frame and returns the current
        active (confirmed) tracks, including any still within their grace period."""
        seen = self.detector.track(frame)
        seen_ids = set()

        for det in seen:
            track_id = det["id"]
            seen_ids.add(track_id)

            if track_id in self._tracks:
                self._tracks[track_id] = {"box": det["box"], "conf": det["conf"], "missed": 0}
                continue

            prior_streak = self._pending.get(track_id, {}).get("streak", 0)
            streak = prior_streak + 1
            if streak >= self.confirm_frames:
                self._tracks[track_id] = {"box": det["box"], "conf": det["conf"], "missed": 0}
                self._pending.pop(track_id, None)
            else:
                self._pending[track_id] = {"box": det["box"], "conf": det["conf"], "streak": streak}

        # A pending (unconfirmed) candidate missed even once - most likely a
        # false positive, drop it immediately rather than granting it a grace period.
        for track_id in list(self._pending.keys()):
            if track_id not in seen_ids:
                del self._pending[track_id]

        for track_id in list(self._tracks.keys()):
            if track_id in seen_ids:
                continue
            self._tracks[track_id]["missed"] += 1
            if self._tracks[track_id]["missed"] > self.grace_frames:
                del self._tracks[track_id]

        self._dedupe_overlapping_tracks()

        return self.active_tracks()

    def _dedupe_overlapping_tracks(self):
        """Collapses pairs of tracks whose boxes overlap heavily into one,
        keeping whichever was actually seen this frame (lower "missed"),
        breaking ties by higher detection confidence."""
        ids = list(self._tracks.keys())
        to_remove = set()

        for i in range(len(ids)):
            id_a = ids[i]
            if id_a in to_remove:
                continue
            for j in range(i + 1, len(ids)):
                id_b = ids[j]
                if id_b in to_remove:
                    continue
                state_a, state_b = self._tracks[id_a], self._tracks[id_b]
                if _iou(state_a["box"], state_b["box"]) < self.dedup_iou:
                    continue
                key_a = (state_a["missed"], -state_a["conf"])
                key_b = (state_b["missed"], -state_b["conf"])
                to_remove.add(id_b if key_a <= key_b else id_a)

        for track_id in to_remove:
            del self._tracks[track_id]

    def active_tracks(self):
        """Returns [{"id", "box", "conf", "is_stale"}] for every track
        currently counted as present (seen this frame or still within its
        grace period)."""
        return [
            {
                "id": track_id,
                "box": state["box"],
                "conf": state["conf"],
                "is_stale": state["missed"] > 0,
            }
            for track_id, state in self._tracks.items()
        ]
