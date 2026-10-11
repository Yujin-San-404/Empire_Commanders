"""Movement primitives and soft separation between overlapping units."""
from __future__ import annotations

import math
from typing import List

from entities.entity import Unit


class MovementSystem:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def clamp_to_bounds(self, unit: Unit) -> None:
        r = unit.radius
        unit.x = min(max(unit.x, r), self.width - r)
        unit.y = min(max(unit.y, r), self.height - r)

    def move_by_direction(self, unit: Unit, dx: float, dy: float, dt: float) -> None:
        """Move along (dx, dy) at the unit's speed. Diagonals are normalised."""
        length = math.hypot(dx, dy)
        if length < 1e-9 or not unit.is_alive:
            return
        step = unit.stats.speed * dt
        unit.x += dx / length * step
        unit.y += dy / length * step
        self.clamp_to_bounds(unit)

    def move_toward(self, unit: Unit, tx: float, ty: float, dt: float,
                    stop_distance: float = 0.0, speed_multiplier: float = 1.0) -> bool:
        """Walk toward a point, never overshooting. Returns True once within
        ``stop_distance`` of it."""
        if not unit.is_alive:
            return False
        dx, dy = tx - unit.x, ty - unit.y
        dist = math.hypot(dx, dy)
        if dist <= stop_distance:
            return True
        step = min(unit.stats.speed * speed_multiplier * dt, dist - stop_distance)
        unit.x += dx / dist * step
        unit.y += dy / dist * step
        self.clamp_to_bounds(unit)
        return dist - step <= stop_distance + 1e-9

    def separate(self, units: List[Unit], strength: float = 0.5) -> None:
        """Push overlapping units apart (O(n^2); fine for tactical-sized armies).

        ``strength`` is the fraction of the overlap resolved per call; heavier
        units (higher ``mass``) are pushed less.
        """
        n = len(units)
        for i in range(n):
            a = units[i]
            for j in range(i + 1, n):
                b = units[j]
                min_dist = a.radius + b.radius
                dx, dy = b.x - a.x, b.y - a.y
                d2 = dx * dx + dy * dy
                if d2 >= min_dist * min_dist:
                    continue
                d = math.sqrt(d2)
                if d < 1e-6:  # exactly stacked: pick a deterministic direction
                    angle = (a.uid * 2.399963 + b.uid) % (2 * math.pi)
                    dx, dy, d = math.cos(angle), math.sin(angle), 1.0
                overlap = (min_dist - d) * strength
                nx, ny = dx / d, dy / d
                total = a.mass + b.mass
                a.x -= nx * overlap * (b.mass / total)
                a.y -= ny * overlap * (b.mass / total)
                b.x += nx * overlap * (a.mass / total)
                b.y += ny * overlap * (a.mass / total)
        for u in units:
            self.clamp_to_bounds(u)
