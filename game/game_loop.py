"""Fixed-timestep accumulator. Pure Python so it can be unit-tested without pygame."""
from __future__ import annotations


class FixedTimestep:
    """Turns variable frame times into a whole number of fixed simulation steps.

    * ``max_frame_time`` clamps a single frame so a stall (window drag, debugger,
      slow disk) cannot produce a huge catch-up.
    * ``max_steps`` caps steps per frame; any surplus time is discarded rather
      than letting the game spiral into ever-longer frames.
    """

    def __init__(self, step: float = 1 / 60, max_frame_time: float = 0.25, max_steps: int = 5) -> None:
        if step <= 0 or max_frame_time <= 0 or max_steps < 1:
            raise ValueError("step, max_frame_time must be > 0 and max_steps >= 1")
        self.step = step
        self.max_frame_time = max_frame_time
        self.max_steps = max_steps
        self._accumulator = 0.0

    def advance(self, frame_dt: float) -> int:
        """Return how many fixed steps to simulate for this frame."""
        self._accumulator += min(max(frame_dt, 0.0), self.max_frame_time)
        steps = 0
        while self._accumulator >= self.step and steps < self.max_steps:
            self._accumulator -= self.step
            steps += 1
        if steps == self.max_steps:
            self._accumulator = 0.0
        return steps

    def reset(self) -> None:
        self._accumulator = 0.0
