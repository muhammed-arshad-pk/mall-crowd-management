"""
Shared per-frame pipeline: person detection -> tracking -> stable aggregate
count -> frame-based entry/exit.

Both app/main.py and webapp/server.py drive the same CrowdEngine so the
detection/tracking/counting logic exists in exactly one place.

Two separate concepts (see README):
  - stable_count_change: the confirmed aggregate count changed - feeds the
    crowd_events register. Fires only on an actual change, never per frame.
  - entry_exit_events: a tracked person appeared (ENTER) or disappeared
    (EXIT) - feeds entry_exit_events and the cumulative Entered/Exited
    totals. The camera's field of view is the entry/exit boundary itself, so
    no virtual line is needed.
"""
from dataclasses import dataclass, field

import config
import overlay
from detector import PersonDetector
from tracker import PersonTracker
from counting import CountStabilizer


@dataclass
class FrameResult:
    active_tracks: list
    current_count: int         # confirmed stable count
    entered: int                # cumulative, from tracks appearing
    exited: int                  # cumulative, from tracks disappearing
    stable_count_change: tuple | None = None   # (previous, new) if the register should log a row this frame
    entry_exit_events: list = field(default_factory=list)  # [(track_id, "ENTER"|"EXIT")]


class CrowdEngine:
    """Owns the model plus all tracking/counting/stability state for one
    camera stream. Not thread-safe on its own - callers that share an
    instance across threads (e.g. the web server) must serialize access."""

    def __init__(self, device=None):
        self.device = device if device is not None else config.resolve_device()

        self.detector = PersonDetector(device=self.device)
        self.tracker = PersonTracker(self.detector)
        self.stabilizer = CountStabilizer()
        self.entered = 0
        self.exited = 0
        self._previous_ids = set()

    def infer(self, frame):
        """Runs the full detection+tracking+counting pipeline on one frame.
        Does NOT draw anything. Returns a FrameResult."""
        active_tracks = self.tracker.update(frame)
        stable_count_change = self.stabilizer.update(len(active_tracks))

        current_ids = {t["id"] for t in active_tracks}
        entered_ids = current_ids - self._previous_ids
        exited_ids = self._previous_ids - current_ids
        self._previous_ids = current_ids

        entry_exit_events = [(tid, "ENTER") for tid in entered_ids] + [(tid, "EXIT") for tid in exited_ids]
        self.entered += len(entered_ids)
        self.exited += len(exited_ids)

        return FrameResult(
            active_tracks=active_tracks,
            current_count=self.stabilizer.stable_count,
            entered=self.entered,
            exited=self.exited,
            stable_count_change=stable_count_change,
            entry_exit_events=entry_exit_events,
        )

    def draw(self, frame, result):
        """Draws every tracked person's box/ID onto frame."""
        overlay.draw_tracks(frame, result.active_tracks)
        return frame
