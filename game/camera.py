"""Viewport: maps the fixed logical resolution onto a resizable window.

The game always renders to a 1280x720 logical surface. This class computes how
that surface is scaled and letterboxed into the real window, and converts mouse
positions back to logical coordinates (pure math, no pygame).
"""
from __future__ import annotations

from typing import Tuple


class Viewport:
    def __init__(self, logical_w: int = 1280, logical_h: int = 720) -> None:
        self.logical_w = logical_w
        self.logical_h = logical_h
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.dest_w = logical_w
        self.dest_h = logical_h

    def update(self, window_w: int, window_h: int) -> None:
        window_w, window_h = max(1, window_w), max(1, window_h)
        self.scale = min(window_w / self.logical_w, window_h / self.logical_h)
        self.dest_w = max(1, int(self.logical_w * self.scale))
        self.dest_h = max(1, int(self.logical_h * self.scale))
        self.offset_x = (window_w - self.dest_w) // 2
        self.offset_y = (window_h - self.dest_h) // 2

    def to_logical(self, wx: float, wy: float) -> Tuple[float, float]:
        return ((wx - self.offset_x) / self.scale, (wy - self.offset_y) / self.scale)

    def contains_window_point(self, wx: float, wy: float) -> bool:
        lx, ly = self.to_logical(wx, wy)
        return 0 <= lx < self.logical_w and 0 <= ly < self.logical_h
