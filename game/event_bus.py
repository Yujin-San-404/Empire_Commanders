"""Tiny synchronous publish/subscribe bus.

Simulation systems publish events (an attack landed, a unit fell); the UI
subscribes to produce feedback such as floating damage numbers. The simulation
never depends on any subscriber existing.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

# Event names
ATTACK = "attack"                # payload: systems.combat_system.AttackResult
UNIT_DEFEATED = "unit_defeated"  # payload: entities.entity.Unit
BATTLE_ENDED = "battle_ended"    # payload: world.battlefield.BattleResult


class EventBus:
    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[[Any], None]) -> None:
        self._handlers[event].append(handler)

    def publish(self, event: str, payload: Any = None) -> None:
        for handler in list(self._handlers.get(event, ())):
            handler(payload)
