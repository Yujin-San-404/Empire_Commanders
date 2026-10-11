"""Application shell: window, main loop, game modes. Phase 1 = one battle."""
from __future__ import annotations

from enum import Enum
from typing import Optional

import pygame

from game.camera import Viewport
from game.config import BattleData, Settings, load_battle_data, load_settings
from game.event_bus import EventBus
from game.game_loop import FixedTimestep
from game.input_manager import Command, CommandKind, InputManager
from ui.battle_renderer import BattleRenderer
from ui.effects import EffectsManager
from ui.hud import Hud
from ui.widgets import Fonts
from world.battlefield import Battlefield, BattleResult

LOGICAL_W, LOGICAL_H = 1280, 720
SCENARIO = "skirmish"


class Mode(Enum):
    PLAYING = "playing"
    PAUSED = "paused"


class Game:
    def __init__(self, settings: Optional[Settings] = None, data: Optional[BattleData] = None) -> None:
        self.settings = settings or load_settings()
        self.data = data or load_battle_data()
        pygame.init()
        flags = pygame.FULLSCREEN if self.settings.fullscreen else pygame.RESIZABLE
        self.window = pygame.display.set_mode((self.settings.window_width, self.settings.window_height), flags)
        pygame.display.set_caption("Empire Commanders")
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.clock = pygame.time.Clock()
        self.viewport = Viewport(LOGICAL_W, LOGICAL_H)
        self.input = InputManager(self.viewport)
        self.events = EventBus()
        self.effects = EffectsManager(self.events)
        self.fonts = Fonts()
        self.hud = Hud(self.fonts, LOGICAL_W, LOGICAL_H)
        self.timestep = FixedTimestep(step=1 / 60, max_frame_time=0.25, max_steps=5)
        self.show_fps = self.settings.show_fps
        self.mode = Mode.PLAYING
        self.running = True
        self.battle: Battlefield
        self.renderer: BattleRenderer
        self.new_battle()

    # --- battle lifecycle ---------------------------------------------
    def new_battle(self) -> None:
        d = self.data
        self.battle = Battlefield.from_scenario(
            d.scenarios[SCENARIO], d.width, d.height, d.general_stats, d.troop_stats,
            d.ai, events=self.events, decoration_seed=d.decoration_seed)
        self.renderer = BattleRenderer(self.battle, self.effects, self.fonts)
        self.effects.clear()
        self.timestep.reset()
        self.mode = Mode.PLAYING

    @property
    def battle_over(self) -> bool:
        return self.battle.result != BattleResult.ONGOING

    # --- commands ------------------------------------------------------
    def handle_command(self, cmd: Command) -> None:
        overlay_active = self.mode == Mode.PAUSED or self.battle_over
        if cmd.kind == CommandKind.QUIT_WINDOW:
            self.running = False
        elif cmd.kind == CommandKind.QUIT_KEY and overlay_active:
            self.running = False
        elif cmd.kind == CommandKind.TOGGLE_PAUSE and not self.battle_over:
            self.mode = Mode.PAUSED if self.mode == Mode.PLAYING else Mode.PLAYING
            self.timestep.reset()
        elif cmd.kind == CommandKind.RESTART and overlay_active:
            self.new_battle()
        elif cmd.kind == CommandKind.SELECT and not overlay_active and cmd.pos is not None:
            self.battle.select_at(*cmd.pos)
        elif cmd.kind == CommandKind.TOGGLE_FPS:
            self.show_fps = not self.show_fps

    # --- main loop -----------------------------------------------------
    def run(self, max_frames: Optional[int] = None) -> None:
        frames = 0
        while self.running:
            frame_dt = self.clock.tick(self.settings.target_fps) / 1000.0
            self.step_frame(frame_dt, pygame.event.get())
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        pygame.quit()

    def step_frame(self, frame_dt: float, events) -> None:
        """One iteration of the loop: input -> update -> render."""
        for cmd in self.input.process_events(events):
            self.handle_command(cmd)
        if self.mode == Mode.PLAYING:
            if not self.battle_over:
                player_input = self.input.player_input()
                for _ in range(self.timestep.advance(frame_dt)):
                    self.battle.update(self.timestep.step, player_input)
            self.effects.update(min(frame_dt, self.timestep.max_frame_time))
        self.render()

    # --- rendering -----------------------------------------------------
    def render(self) -> None:
        self.renderer.draw(self.canvas)
        fps = self.clock.get_fps() if self.show_fps else None
        self.hud.draw(self.canvas, self.battle, fps)
        if self.battle_over:
            self.hud.draw_result(self.canvas, self.battle)
        elif self.mode == Mode.PAUSED:
            self.hud.draw_pause(self.canvas)
        self._present()

    def _present(self) -> None:
        window = pygame.display.get_surface() or self.window
        self.viewport.update(*window.get_size())
        window.fill((0, 0, 0))
        if self.viewport.scale == 1.0:
            window.blit(self.canvas, (self.viewport.offset_x, self.viewport.offset_y))
        else:
            scaled = pygame.transform.smoothscale(self.canvas, (self.viewport.dest_w, self.viewport.dest_h))
            window.blit(scaled, (self.viewport.offset_x, self.viewport.offset_y))
        pygame.display.flip()
