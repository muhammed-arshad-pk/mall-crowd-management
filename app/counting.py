"""
Stable aggregate-count debounce.

Separate from tracker.py's per-track confirm/grace logic - this stabilizes
the *reported* current count. A change is only confirmed once the new count
holds for config.COUNT_CONFIRMATION_FRAMES consecutive frames, so a single
fluctuating frame never produces a confirmed change or a register event.
"""
import config


class CountStabilizer:
    def __init__(self, confirm_frames=config.COUNT_CONFIRMATION_FRAMES):
        self.confirm_frames = confirm_frames
        self.stable_count = 0
        self._candidate = None
        self._streak = 0

    def update(self, raw_count):
        """Feed one frame's raw count. Returns (previous_stable, new_stable)
        if a confirmed change just happened this frame, else None."""
        if raw_count == self.stable_count:
            self._candidate = None
            self._streak = 0
            return None

        if raw_count == self._candidate:
            self._streak += 1
        else:
            self._candidate = raw_count
            self._streak = 1

        if self._streak >= self.confirm_frames:
            previous = self.stable_count
            self.stable_count = raw_count
            self._candidate = None
            self._streak = 0
            return previous, self.stable_count

        return None
