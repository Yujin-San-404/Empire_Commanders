"""Soldier creation helpers (allied and enemy soldiers share the Unit model)."""
from __future__ import annotations

from entities.entity import Team, Unit, UnitStats


def create_soldier(uid: int, team: Team, stats: UnitStats, x: float, y: float) -> Unit:
    return Unit(uid=uid, team=team, stats=stats, x=x, y=y)
