"""Short-lived visual feedback (swings, damage numbers, defeat puffs).

Effects are render-side only: they listen to simulation events and never touch
gameplay state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from entities.entity import Team, Unit
from game import event_bus
from game.event_bus import EventBus
from systems.combat_system import AttackResult


@dataclass
class Effect:
    kind: str                 # "swing", "damage", "puff"
    x: float
    y: float
    duration: float
    age: float = 0.0
    text: str = ""
    to_x: float = 0.0         # swing end point
    to_y: float = 0.0
    team: Team = Team.ENEMY   # whose unit was hit / defeated (colour choice)
    size: float = 10.0

    @property
    def progress(self) -> float:
        return min(1.0, self.age / self.duration)


class EffectsManager:
    MAX_EFFECTS = 200

    def __init__(self, events: EventBus) -> None:
        self.effects: List[Effect] = []
        events.subscribe(event_bus.ATTACK, self._on_attack)
        events.subscribe(event_bus.UNIT_DEFEATED, self._on_defeated)

    def _add(self, effect: Effect) -> None:
        if len(self.effects) < self.MAX_EFFECTS:
            self.effects.append(effect)

    def _on_attack(self, r: AttackResult) -> None:
        ax, ay = r.attacker_pos
        tx, ty = r.target_pos
        self._add(Effect("swing", ax, ay, 0.15, to_x=tx, to_y=ty, team=r.target_team))
        self._add(Effect("damage", tx, ty - 14, 0.8, text=f"-{r.damage:.0f}", team=r.target_team))

    def _on_defeated(self, unit: Unit) -> None:
        self._add(Effect("puff", unit.x, unit.y, 0.45, team=unit.team, size=unit.radius))

    def update(self, dt: float) -> None:
        for e in self.effects:
            e.age += dt
        self.effects = [e for e in self.effects if e.age < e.duration]

    def clear(self) -> None:
        self.effects.clear()
