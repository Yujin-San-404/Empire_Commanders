# Empire Commanders — Phase 1 build

A top-down medieval army-command game written in Python + Pygame.
**This is Phase 1 of 6: the core battlefield.** See "Status" below for exactly what exists.

## Setup and launch

```bash
python -m venv .venv && source .venv/bin/activate      # optional (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
python main.py
```

Run the tests:

```bash
python -m unittest discover -s tests -t . -v
```

Smoke-run N frames and exit: `python main.py --frames 300`

## Controls

| Input | Action |
|---|---|
| WASD / Arrow keys | Move the general |
| Space (hold) | Melee attack (nearest enemy in reach, or your selected target) |
| Left-click | Select an enemy (click empty ground to deselect) |
| Esc | Pause / resume |
| R | Restart battle (from pause or result screen) |
| Enter | New battle (result screen) |
| Q | Quit (from pause or result screen) |
| F3 | Toggle FPS counter |

The window is resizable; the game renders at 1280×720 and is scaled/letterboxed.

## How Phase 1 plays

You are the general (gold crown) with four Bolo Fighters following you. Five raiders
(3 Bolo Fighters, 2 Spearmen) wait on the east side and attack anyone who comes within
240 px. Your soldiers keep a spaced ring around you and automatically engage enemies
near you. Win by defeating every raider; lose if the general falls.

## Status

**Implemented (Phase 1)**
- Window, scaled/letterboxed rendering, fixed-timestep loop (60 Hz simulation, frame-spike clamp), pause that freezes the simulation
- General movement, cooldown-limited melee attack, click target selection
- Four allied soldiers: follow ring slots (distinct positions), auto-engage, catch-up speed, separation
- Enemy squad AI: idle → aggro → chase → fight, with leash
- Centralised combat (range, cooldown, team, alive checks; damage applied exactly once), target prioritisation (nearest, wounded favoured)
- Health bars, damage numbers, swing/defeat effects, victory/defeat screens, battle stats
- Data-driven unit stats, AI tuning and scenario (`data/*.json`), validated on load; `settings.json` falls back to defaults if broken

**Not implemented yet (later phases)**
Army orders (F/H/C and the command panel), right-click move, A* pathfinding and blocking obstacles, formations, ranged combat, other troop classes, village/economy/recruitment, world map, campaign, difficulty, save/load, menus beyond pause/result, audio, morale. Multiplayer/Android are out of scope.

## Design notes and deviations from the proposed layout

- Soldiers and enemies share one `Unit` class (`entities/entity.py`); `entities/enemy.py`, `projectile.py`, `game/game_state.py`, `game/camera.py` (a `Viewport` for window scaling lives there) and the other proposed modules are not created until they have real work to do.
- Alive/defeated is **derived** from `health > 0` — there is no separate state flag to drift out of sync.
- Range is centre-to-centre: `distance <= attack_range + attacker.radius + target.radius`.
- Decorative trees and rocks are **non-blocking** in Phase 1 (documented simplification; obstacles + A* come in Phase 2).
- Defeated units are removed from the battlefield at the end of each step, and every reference to them (targets, selection) is cleared.
- Simulation, AI and combat code never import pygame; only `game/game.py`, `game/input_manager.py` and `ui/` do.

## Verification report (what was actually run)

Environment where this was built: Python 3.12, **no pygame available (no network)**.

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -t .` (simulation, combat, movement, config, timestep, viewport) | **60 tests passed**, 1 smoke test skipped (pygame absent) |
| Deliberate bug injection (5 mutations of cooldown, range, damage clamp, overshoot, selection cleanup) | 4 caught immediately; the overshoot one exposed a test gap, which was then fixed and re-verified |
| Scripted bot vs the scenario at 30, 60 and 120 steps/s | Victory each time (~9 s sim time, general ends ~22/150 HP, 4/4 soldiers alive) |
| Game loop wired to a *fake* pygame stand-in (input, click-select through scaling, pause, victory, restart, spike clamp, quit gating) | Passed — this checks my wiring only, **not** real pygame behaviour |

**Not verified:** actual window launch, real rendering/visuals, real keyboard/mouse feel, FPS, Python versions other than 3.12.
`tests/test_smoke.py` runs the real game headlessly once pygame is installed — it has **not been executed yet**. Please run the test command above after installing pygame; if it or `python main.py` fails, that is a real Phase 1 bug to fix before Phase 2.

## Known limitations

- Visuals are placeholder shapes drawn with Pygame primitives.
- Battle balance is hand-tuned from a scripted bot, not from human playtesting.
- Allies only follow/auto-engage; you cannot give them orders yet.
- Units walk through decorations and cannot path around anything (no obstacles exist yet).

## Next step: Phase 2

Orders (Follow/Move/Hold/Charge via F/H/C + right-click), grid + A* pathfinding with blocking obstacles, formation positions, and a command panel.
