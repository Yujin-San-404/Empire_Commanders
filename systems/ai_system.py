"""Behaviour for allied soldiers and enemies (Phase 1: follow + auto-engage)."""
from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import Any, Dict, List, Optional

from entities.entity import Order, Team, Unit
from entities.general import General
from systems.combat_system import CombatSystem
from systems.formation_system import follow_slots
from systems.movement_system import MovementSystem


@dataclass(frozen=True)
class AIConfig:
    enemy_aggro_radius: float = 240.0      # enemies notice player units this close
    enemy_leash_radius: float = 560.0      # enemies give up a chase beyond this
    ally_engage_radius: float = 180.0      # soldiers engage enemies this close
    ally_leash_radius: float = 340.0       # ...but only if the enemy is this close to the general
    ally_return_radius: float = 430.0      # soldiers disengage if the fight drifts this far from the general
    follow_ring_radius: float = 55.0
    follow_ring_spacing: float = 36.0
    follow_ring_capacity: int = 6
    follow_arrive_distance: float = 8.0
    catch_up_distance: float = 220.0       # soldiers this far behind the general speed up
    catch_up_multiplier: float = 1.5
    chase_stop_fraction: float = 0.85      # stop chasing at this fraction of weapon reach

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIConfig":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown AI settings: {', '.join(sorted(unknown))}")
        cfg = cls(**data)
        for f in fields(cls):
            if float(getattr(cfg, f.name)) <= 0:
                raise ValueError(f"AI setting '{f.name}' must be greater than 0")
        if not 0 < cfg.chase_stop_fraction < 1:
            raise ValueError("AI setting 'chase_stop_fraction' must be between 0 and 1")
        return cfg


class AISystem:
    def __init__(self, combat: CombatSystem, movement: MovementSystem, config: AIConfig) -> None:
        self.combat = combat
        self.movement = movement
        self.cfg = config

    def update(self, units_by_id: Dict[int, Unit], general: Optional[General], dt: float) -> None:
        """``general`` must be None when the general has been defeated."""
        alive = [u for u in units_by_id.values() if u.is_alive]
        players = [u for u in alive if u.team == Team.PLAYER]
        enemies = [u for u in alive if u.team == Team.ENEMY]
        soldiers = sorted((u for u in players if not isinstance(u, General)), key=lambda u: u.uid)

        slots: List[tuple] = []
        if general is not None:
            c = self.cfg
            slots = follow_slots(general.x, general.y, len(soldiers), c.follow_ring_radius,
                                 c.follow_ring_spacing, c.follow_ring_capacity)
        for index, soldier in enumerate(soldiers):
            self._update_ally(soldier, slots[index] if slots else None,
                              units_by_id, enemies, general, dt)
        for enemy in enemies:
            self._update_enemy(enemy, units_by_id, players, dt)

    # --- helpers -------------------------------------------------------
    @staticmethod
    def _current_target(unit: Unit, units_by_id: Dict[int, Unit]) -> Optional[Unit]:
        if unit.target_id is None:
            return None
        t = units_by_id.get(unit.target_id)
        if t is None or not t.is_alive or t.team == unit.team:
            return None
        return t

    def _engage(self, unit: Unit, target: Unit, dt: float) -> None:
        if self.combat.in_range(unit, target):
            self.combat.try_attack(unit, target)
        else:
            stop = self.combat.reach(unit, target) * self.cfg.chase_stop_fraction
            self.movement.move_toward(unit, target.x, target.y, dt, stop_distance=stop)

    # --- allies --------------------------------------------------------
    def _update_ally(self, unit: Unit, slot: Optional[tuple], units_by_id: Dict[int, Unit],
                     enemies: List[Unit], general: Optional[General], dt: float) -> None:
        c = self.cfg
        target = self._current_target(unit, units_by_id)
        if target is not None and general is not None and general.distance_to(target) > c.ally_return_radius:
            target = None  # the fight drifted too far from the general: come back

        if target is None:
            candidates = enemies
            if general is not None:
                candidates = [e for e in enemies if general.distance_to(e) <= c.ally_leash_radius]
            target = self.combat.find_target(unit, candidates, c.ally_engage_radius)

        if target is not None:
            unit.target_id = target.uid
            unit.order = Order.ATTACK
            self._engage(unit, target, dt)
            return

        unit.target_id = None
        if general is None or slot is None:
            unit.order = Order.IDLE
            return
        unit.order = Order.FOLLOW
        far = general.distance_to(unit) > c.catch_up_distance
        self.movement.move_toward(unit, slot[0], slot[1], dt,
                                  stop_distance=c.follow_arrive_distance,
                                  speed_multiplier=c.catch_up_multiplier if far else 1.0)

    # --- enemies -------------------------------------------------------
    def _update_enemy(self, unit: Unit, units_by_id: Dict[int, Unit],
                      players: List[Unit], dt: float) -> None:
        target = self._current_target(unit, units_by_id)
        if target is not None and unit.distance_to(target) > self.cfg.enemy_leash_radius:
            target = None
        if target is None:
            target = self.combat.find_target(unit, players, self.cfg.enemy_aggro_radius)
        if target is None:
            unit.target_id = None
            unit.order = Order.IDLE
            return
        unit.target_id = target.uid
        unit.order = Order.ATTACK
        self._engage(unit, target, dt)
