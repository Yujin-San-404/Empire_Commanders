"""Formation slot generation. Phase 1 provides follow slots only."""
from __future__ import annotations

import math
from typing import List, Tuple


def follow_slots(cx: float, cy: float, count: int, ring_radius: float,
                 ring_spacing: float, ring_capacity: int) -> List[Tuple[float, float]]:
    """Distinct positions on concentric rings around (cx, cy).

    Every soldier gets its own slot, so followers spread out instead of piling
    onto the general's position.
    """
    slots: List[Tuple[float, float]] = []
    for i in range(count):
        ring = i // ring_capacity
        in_ring = min(ring_capacity, count - ring * ring_capacity)
        k = i % ring_capacity
        angle = 2 * math.pi * k / in_ring + ring * math.pi / max(in_ring, 1)
        radius = ring_radius + ring * ring_spacing
        slots.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return slots
