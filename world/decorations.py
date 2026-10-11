"""Decorative trees and rocks.

Phase 1 decision: decorations are purely visual and NON-BLOCKING. Units walk
through them. Blocking obstacles and pathfinding arrive in Phase 2.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class Decoration:
    kind: str      # "tree" or "rock"
    x: float
    y: float
    size: float


def generate_decorations(width: float, height: float, seed: int,
                         keep_clear: Sequence[Tuple[float, float, float]] = (),
                         count: int = 38) -> List[Decoration]:
    """Deterministic scatter of decorations; ``keep_clear`` is (x, y, radius) zones."""
    rng = random.Random(seed)
    out: List[Decoration] = []
    attempts = 0
    while len(out) < count and attempts < count * 20:
        attempts += 1
        x, y = rng.uniform(20, width - 20), rng.uniform(20, height - 20)
        if any(math.hypot(x - cx, y - cy) < r for cx, cy, r in keep_clear):
            continue
        kind = "tree" if rng.random() < 0.65 else "rock"
        size = rng.uniform(14, 24) if kind == "tree" else rng.uniform(8, 15)
        out.append(Decoration(kind, x, y, size))
    return out
