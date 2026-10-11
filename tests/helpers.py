"""Shared test helpers (no pygame needed)."""
import math

from entities.entity import Team, Unit, UnitStats
from game.config import load_battle_data
from world.battlefield import Battlefield, PlayerInput

DATA = load_battle_data()


def make_stats(**over):
    base = dict(unit_class="test", display_name="Test", max_health=50, damage=10,
                attack_range=20, attack_cooldown=1.0, speed=100, radius=10)
    base.update(over)
    return UnitStats(**base)


def make_unit(uid=1, team=Team.PLAYER, x=0.0, y=0.0, **stats):
    return Unit(uid=uid, team=team, stats=make_stats(**stats), x=x, y=y)


def skirmish(events=None):
    return Battlefield.from_scenario(DATA.scenarios["skirmish"], DATA.width, DATA.height,
                                     DATA.general_stats, DATA.troop_stats, DATA.ai,
                                     events=events, decoration_seed=DATA.decoration_seed)


def bot_input(bf):
    """A simple scripted player: walk to the nearest enemy and hold attack."""
    g = bf.general
    foes = bf.enemies()
    if not foes:
        return PlayerInput()
    t = min(foes, key=lambda e: g.distance_to(e))
    dx, dy = t.x - g.x, t.y - g.y
    d = math.hypot(dx, dy)
    move = d > bf.combat.reach(g, t) * 0.8
    return PlayerInput(dx / d if move else 0, dy / d if move else 0, True)
