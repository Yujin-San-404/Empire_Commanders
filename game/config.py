"""Loading and validating settings and game data. Bad files fall back safely."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict

from entities.entity import UnitStats
from systems.ai_system import AIConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DataError(Exception):
    """Raised when a required game data file is missing or invalid."""


def load_json(path: Path) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise DataError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"Invalid JSON in {path}: {exc}") from exc


@dataclass(frozen=True)
class Settings:
    window_width: int = 1280
    window_height: int = 720
    target_fps: int = 60
    fullscreen: bool = False
    show_fps: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        s = cls(**{f.name: data[f.name] for f in fields(cls) if f.name in data})
        if not (isinstance(s.window_width, int) and isinstance(s.window_height, int)
                and s.window_width >= 640 and s.window_height >= 360):
            raise ValueError("window size must be integers of at least 640x360")
        if not (isinstance(s.target_fps, int) and 15 <= s.target_fps <= 240):
            raise ValueError("target_fps must be an integer from 15 to 240")
        if not (isinstance(s.fullscreen, bool) and isinstance(s.show_fps, bool)):
            raise ValueError("fullscreen and show_fps must be true or false")
        return s


def load_settings(path: Path = PROJECT_ROOT / "settings.json") -> Settings:
    """Never raises: a missing or malformed settings file yields defaults + a warning."""
    try:
        data = load_json(path)
        if not isinstance(data, dict):
            raise ValueError("settings must be a JSON object")
        return Settings.from_dict(data)
    except (DataError, ValueError, TypeError) as exc:
        print(f"[warning] Using default settings ({exc})", file=sys.stderr)
        return Settings()


@dataclass(frozen=True)
class BattleData:
    width: int
    height: int
    decoration_seed: int
    general_stats: UnitStats
    troop_stats: Dict[str, UnitStats]
    ai: AIConfig
    scenarios: Dict[str, Dict[str, Any]]


def load_battle_data(data_dir: Path = PROJECT_ROOT / "data") -> BattleData:
    troops = load_json(data_dir / "troops.json")
    battle = load_json(data_dir / "battle.json")
    try:
        general = UnitStats.from_dict("general", troops["general"])
        troop_stats = {cid: UnitStats.from_dict(cid, d) for cid, d in troops["troops"].items()}
        bf = battle["battlefield"]
        scenarios = battle["scenarios"]
        data = BattleData(int(bf["width"]), int(bf["height"]), int(bf.get("decoration_seed", 0)),
                          general, troop_stats, AIConfig.from_dict(battle["ai"]), scenarios)
    except (KeyError, TypeError, ValueError) as exc:
        raise DataError(f"Invalid game data: {exc!r}") from exc
    for name, sc in scenarios.items():
        classes = [g["class"] for g in sc.get("ally_squad", [])] + [e["class"] for e in sc.get("enemy_squad", [])]
        unknown = [c for c in classes if c not in troop_stats]
        if unknown:
            raise DataError(f"Scenario '{name}' uses unknown troop classes: {', '.join(unknown)}")
    return data
