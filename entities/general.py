"""The player-controlled general."""
from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Unit


@dataclass(eq=False)
class General(Unit):
    """The player's commander.

    Heavier than ordinary soldiers so a walking general is not shoved around by
    his own men. Equipment, skills and recovery rules (later phases) attach here.
    """
    mass = 3.0
