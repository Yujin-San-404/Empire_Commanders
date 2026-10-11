"""Centralised attack validation and resolution.

Every attack in the game goes through ``CombatSystem.try_attack``. Range is
measured centre-to-centre: a target is in range when

    distance <= attacker.attack_range + attacker.radius + target.radius

i.e. ``attack_range`` is the reach beyond the two body edges.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional

from entities.entity import Team, Unit
from game import event_bus
from game.event_bus import EventBus


class AttackDenied(Enum):
    ATTACKER_DEFEATED = "attacker is defeated"
    TARGET_DEFEATED = "target is defeated"
    SELF_TARGET = "a unit cannot attack itself"
    FRIENDLY_FIRE = "a unit cannot attack its own team"
    OUT_OF_RANGE = "target is out of range"
    ON_COOLDOWN = "attack is on cooldown"


@dataclass(frozen=True)
class AttackResult:
    attacker_id: int
    target_id: int
    damage: float            # health actually removed
    target_defeated: bool
    target_team: Team
    attacker_pos: tuple
    target_pos: tuple


class CombatSystem:
    def __init__(self, events: Optional[EventBus] = None) -> None:
        self.events = events or EventBus()

    # --- queries -------------------------------------------------------
    @staticmethod
    def reach(attacker: Unit, target: Unit) -> float:
        return attacker.stats.attack_range + attacker.radius + target.radius

    def in_range(self, attacker: Unit, target: Unit) -> bool:
        return attacker.distance_to(target) <= self.reach(attacker, target)

    def validate_attack(self, attacker: Unit, target: Unit) -> Optional[AttackDenied]:
        """Return why the attack is not allowed, or None if it is."""
        if not attacker.is_alive:
            return AttackDenied.ATTACKER_DEFEATED
        if not target.is_alive:
            return AttackDenied.TARGET_DEFEATED
        if attacker is target:
            return AttackDenied.SELF_TARGET
        if attacker.team == target.team:
            return AttackDenied.FRIENDLY_FIRE
        if not self.in_range(attacker, target):
            return AttackDenied.OUT_OF_RANGE
        if attacker.cooldown_remaining > 0:
            return AttackDenied.ON_COOLDOWN
        return None

    def find_target(self, attacker: Unit, candidates: Iterable[Unit],
                    max_distance: float) -> Optional[Unit]:
        """Pick the best living enemy within ``max_distance`` (centre-to-centre).

        Priority: nearest first, but wounded enemies count as closer
        (score = distance * (0.7 + 0.3 * health_fraction)), so units finish off
        weakened foes. Ties go to the earliest candidate (lowest uid).
        """
        best: Optional[Unit] = None
        best_score = math.inf
        for c in candidates:
            if not c.is_alive or c.team == attacker.team:
                continue
            d = attacker.distance_to(c)
            if d > max_distance:
                continue
            score = d * (0.7 + 0.3 * c.health_fraction)
            if score < best_score:
                best, best_score = c, score
        return best

    # --- actions -------------------------------------------------------
    def try_attack(self, attacker: Unit, target: Unit) -> Optional[AttackResult]:
        """Resolve one attack. Applies damage exactly once, or does nothing."""
        if self.validate_attack(attacker, target) is not None:
            return None
        attacker.cooldown_remaining = attacker.stats.attack_cooldown
        dealt = target.take_damage(attacker.stats.damage)
        result = AttackResult(
            attacker_id=attacker.uid,
            target_id=target.uid,
            damage=dealt,
            target_defeated=not target.is_alive,
            target_team=target.team,
            attacker_pos=attacker.position,
            target_pos=target.position,
        )
        self.events.publish(event_bus.ATTACK, result)
        if result.target_defeated:
            self.events.publish(event_bus.UNIT_DEFEATED, target)
        return result

    @staticmethod
    def tick_cooldowns(units: Iterable[Unit], dt: float) -> None:
        for u in units:
            if u.cooldown_remaining > 0:
                u.cooldown_remaining = max(0.0, u.cooldown_remaining - dt)
