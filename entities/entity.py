"""Core unit model shared by the general, allied soldiers and enemies."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class Team(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"


class Order(Enum):
    """What a unit is currently doing.

    Phase 1 only needs three. Later phases extend this (MOVE, HOLD, CHARGE,
    RETREAT, FORMATION...) as the commands that use them are implemented.
    """
    IDLE = "idle"        # standing still, watching for enemies
    FOLLOW = "follow"    # keeping a slot near the general
    ATTACK = "attack"    # chasing / fighting the unit in ``target_id``


@dataclass(frozen=True)
class UnitStats:
    """Immutable, data-driven combat statistics for one unit class."""
    unit_class: str
    display_name: str
    max_health: float
    damage: float
    attack_range: float      # reach beyond the two body radii; see CombatSystem.reach
    attack_cooldown: float   # seconds between attacks
    speed: float             # pixels per second
    radius: float = 10.0     # body radius in pixels

    @classmethod
    def from_dict(cls, unit_class: str, data: Dict[str, Any]) -> "UnitStats":
        required = ("max_health", "damage", "attack_range", "attack_cooldown", "speed")
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"Unit class '{unit_class}' is missing fields: {', '.join(missing)}")
        try:
            stats = cls(
                unit_class=unit_class,
                display_name=str(data.get("display_name", unit_class.replace("_", " ").title())),
                max_health=float(data["max_health"]),
                damage=float(data["damage"]),
                attack_range=float(data["attack_range"]),
                attack_cooldown=float(data["attack_cooldown"]),
                speed=float(data["speed"]),
                radius=float(data.get("radius", 10.0)),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unit class '{unit_class}' has a non-numeric stat: {exc}") from exc
        for name in ("max_health", "damage", "attack_cooldown", "speed", "radius"):
            if getattr(stats, name) <= 0:
                raise ValueError(f"Unit class '{unit_class}': {name} must be greater than 0")
        if stats.attack_range < 0:
            raise ValueError(f"Unit class '{unit_class}': attack_range cannot be negative")
        return stats


@dataclass(eq=False)
class Unit:
    """A combatant. Alive/defeated is derived from ``health`` (single source of truth)."""
    uid: int
    team: Team
    stats: UnitStats
    x: float
    y: float
    health: float = field(init=False)
    order: Order = Order.IDLE
    target_id: Optional[int] = None
    cooldown_remaining: float = 0.0

    # Relative weight when overlapping units push each other apart.
    mass = 1.0

    def __post_init__(self) -> None:
        self.health = self.stats.max_health

    # --- derived state -------------------------------------------------
    @property
    def is_alive(self) -> bool:
        return self.health > 0

    @property
    def max_health(self) -> float:
        return self.stats.max_health

    @property
    def health_fraction(self) -> float:
        return max(0.0, min(1.0, self.health / self.stats.max_health))

    @property
    def radius(self) -> float:
        return self.stats.radius

    @property
    def position(self) -> tuple:
        return (self.x, self.y)

    def distance_to(self, other: "Unit") -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    # --- state changes -------------------------------------------------
    def take_damage(self, amount: float) -> float:
        """Apply damage; returns the health actually removed. Never goes below 0."""
        if not self.is_alive or amount <= 0:
            return 0.0
        applied = min(self.health, amount)
        self.health -= applied
        if not self.is_alive:
            self.on_defeated()
        return applied

    def on_defeated(self) -> None:
        """A defeated unit stops fighting and drops all orders."""
        self.health = 0.0
        self.target_id = None
        self.order = Order.IDLE
        self.cooldown_remaining = 0.0
