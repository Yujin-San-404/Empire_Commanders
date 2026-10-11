"""The tactical battlefield: owns units and runs one simulation step."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from entities.entity import Team, Unit, UnitStats
from entities.general import General
from entities.soldier import create_soldier
from game import event_bus
from game.event_bus import EventBus
from systems.ai_system import AIConfig, AISystem
from systems.combat_system import CombatSystem
from systems.formation_system import follow_slots
from systems.movement_system import MovementSystem
from world.decorations import Decoration, generate_decorations


class BattleResult(Enum):
    ONGOING = "ongoing"
    VICTORY = "victory"
    DEFEAT = "defeat"


@dataclass
class PlayerInput:
    """What the player is asking the general to do this step."""
    move_x: float = 0.0      # -1..1
    move_y: float = 0.0      # -1..1 (positive = down the screen)
    attack_held: bool = False


class Battlefield:
    def __init__(self, width: float, height: float, general_stats: UnitStats,
                 troop_stats: Dict[str, UnitStats], ai_config: AIConfig,
                 events: Optional[EventBus] = None, decoration_seed: int = 0,
                 title: str = "Battle", objective: str = "") -> None:
        self.width = width
        self.height = height
        self.title = title
        self.objective = objective
        self.events = events or EventBus()
        self.general_stats = general_stats
        self.troop_stats = troop_stats
        self.combat = CombatSystem(self.events)
        self.movement = MovementSystem(width, height)
        self.ai = AISystem(self.combat, self.movement, ai_config)
        self.ai_config = ai_config
        self.units: Dict[int, Unit] = {}     # living units only
        self.general: Optional[General] = None
        self.selected_target_id: Optional[int] = None
        self.result = BattleResult.ONGOING
        self.elapsed = 0.0
        self.allies_lost = 0          # soldiers (not the general) defeated this battle
        self.enemies_defeated = 0
        self.decorations: List[Decoration] = []
        self.decoration_seed = decoration_seed
        self._next_uid = 1

    # --- construction --------------------------------------------------
    @classmethod
    def from_scenario(cls, scenario: Dict[str, Any], width: float, height: float,
                      general_stats: UnitStats, troop_stats: Dict[str, UnitStats],
                      ai_config: AIConfig, events: Optional[EventBus] = None,
                      decoration_seed: int = 0) -> "Battlefield":
        bf = cls(width, height, general_stats, troop_stats, ai_config, events,
                 decoration_seed, scenario.get("title", "Battle"), scenario.get("objective", ""))
        gx, gy = scenario["general_position"]
        bf.spawn_general(gx, gy)

        ally_classes: List[str] = []
        for group in scenario.get("ally_squad", []):
            ally_classes += [group["class"]] * int(group["count"])
        c = ai_config
        slots = follow_slots(gx, gy, len(ally_classes), c.follow_ring_radius,
                             c.follow_ring_spacing, c.follow_ring_capacity)
        for class_id, (sx, sy) in zip(ally_classes, slots):
            bf.spawn_unit(Team.PLAYER, class_id, sx, sy)
        for e in scenario.get("enemy_squad", []):
            bf.spawn_unit(Team.ENEMY, e["class"], e["x"], e["y"])

        keep_clear = [(gx, gy, 140.0)] + [(e["x"], e["y"], 60.0) for e in scenario.get("enemy_squad", [])]
        bf.decorations = generate_decorations(width, height, decoration_seed, keep_clear)
        return bf

    def _new_uid(self) -> int:
        uid = self._next_uid
        self._next_uid += 1
        return uid

    def spawn_general(self, x: float, y: float) -> General:
        if self.general is not None:
            raise RuntimeError("This battlefield already has a general")
        g = General(self._new_uid(), Team.PLAYER, self.general_stats, x, y)
        self.units[g.uid] = g
        self.general = g
        return g

    def spawn_unit(self, team: Team, class_id: str, x: float, y: float) -> Unit:
        if class_id not in self.troop_stats:
            raise KeyError(f"Unknown troop class '{class_id}'")
        u = create_soldier(self._new_uid(), team, self.troop_stats[class_id], x, y)
        self.movement.clamp_to_bounds(u)
        self.units[u.uid] = u
        return u

    # --- queries -------------------------------------------------------
    @property
    def general_alive(self) -> bool:
        return self.general is not None and self.general.is_alive

    def allied_soldiers(self) -> List[Unit]:
        return [u for u in self.units.values()
                if u.team == Team.PLAYER and u is not self.general and u.is_alive]

    def enemies(self) -> List[Unit]:
        return [u for u in self.units.values() if u.team == Team.ENEMY and u.is_alive]

    def get_unit(self, uid: Optional[int]) -> Optional[Unit]:
        return self.units.get(uid) if uid is not None else None

    # --- player commands ----------------------------------------------
    def select_at(self, x: float, y: float, pick_radius: float = 8.0) -> Optional[Unit]:
        """Select the living enemy under (x, y); clicking empty ground clears selection."""
        best: Optional[Unit] = None
        best_d = math.inf
        for e in self.enemies():
            d = math.hypot(e.x - x, e.y - y)
            if d <= e.radius + pick_radius and d < best_d:
                best, best_d = e, d
        self.selected_target_id = best.uid if best else None
        return best

    # --- simulation ----------------------------------------------------
    def update(self, dt: float, player_input: Optional[PlayerInput] = None) -> None:
        """Advance one fixed simulation step."""
        if self.result != BattleResult.ONGOING or dt <= 0:
            return
        self.elapsed += dt
        living = list(self.units.values())
        self.combat.tick_cooldowns(living, dt)

        if self.general_alive and player_input is not None:
            self._update_general(player_input, dt)

        self.ai.update(self.units, self.general if self.general_alive else None, dt)
        self.movement.separate([u for u in self.units.values() if u.is_alive])
        self._cleanup()
        self._evaluate_result()

    def _update_general(self, inp: PlayerInput, dt: float) -> None:
        g = self.general
        assert g is not None
        self.movement.move_by_direction(g, inp.move_x, inp.move_y, dt)
        if not inp.attack_held:
            return
        target = self._general_attack_target()
        if target is not None:
            self.combat.try_attack(g, target)

    def _general_attack_target(self) -> Optional[Unit]:
        """Selected enemy if in reach, otherwise the nearest enemy in reach."""
        g = self.general
        assert g is not None
        selected = self.get_unit(self.selected_target_id)
        if selected is not None and selected.is_alive and self.combat.in_range(g, selected):
            return selected
        in_reach = [e for e in self.enemies() if self.combat.in_range(g, e)]
        return min(in_reach, key=lambda e: g.distance_to(e), default=None)

    def _cleanup(self) -> None:
        """Remove defeated units and clear every reference to them."""
        dead = [uid for uid, u in self.units.items() if not u.is_alive]
        for uid in dead:
            u = self.units.pop(uid)
            if u is self.general:
                continue
            if u.team == Team.PLAYER:
                self.allies_lost += 1
            else:
                self.enemies_defeated += 1
        if self.selected_target_id not in self.units:
            self.selected_target_id = None
        for u in self.units.values():
            if u.target_id is not None and u.target_id not in self.units:
                u.target_id = None

    def _evaluate_result(self) -> None:
        if not self.general_alive:
            self.result = BattleResult.DEFEAT       # defeat wins if both fall on the same step
        elif not self.enemies():
            self.result = BattleResult.VICTORY
        if self.result != BattleResult.ONGOING:
            self.events.publish(event_bus.BATTLE_ENDED, self.result)
