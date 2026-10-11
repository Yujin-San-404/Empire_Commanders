"""Translates pygame keyboard/mouse input into game commands and player input."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, List, Optional, Tuple

import pygame

from game.camera import Viewport
from world.battlefield import PlayerInput


class CommandKind(Enum):
    QUIT_WINDOW = "quit_window"      # window close button
    QUIT_KEY = "quit_key"            # Q on pause / result screens
    TOGGLE_PAUSE = "toggle_pause"    # Escape
    RESTART = "restart"              # R or Enter on pause / result screens
    SELECT = "select"                # left click on the battlefield
    TOGGLE_FPS = "toggle_fps"        # F3


@dataclass(frozen=True)
class Command:
    kind: CommandKind
    pos: Optional[Tuple[float, float]] = None   # logical coordinates for SELECT


class InputManager:
    def __init__(self, viewport: Viewport) -> None:
        self.viewport = viewport
        # Tests/smoke runs can set this to drive the general without a keyboard.
        self.scripted: Optional[Callable[[], PlayerInput]] = None

    def process_events(self, events: Iterable["pygame.event.Event"]) -> List[Command]:
        commands: List[Command] = []
        for event in events:
            if event.type == pygame.QUIT:
                commands.append(Command(CommandKind.QUIT_WINDOW))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    commands.append(Command(CommandKind.TOGGLE_PAUSE))
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                    commands.append(Command(CommandKind.RESTART))
                elif event.key == pygame.K_q:
                    commands.append(Command(CommandKind.QUIT_KEY))
                elif event.key == pygame.K_F3:
                    commands.append(Command(CommandKind.TOGGLE_FPS))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.viewport.contains_window_point(*event.pos):
                    commands.append(Command(CommandKind.SELECT, self.viewport.to_logical(*event.pos)))
        return commands

    def player_input(self) -> PlayerInput:
        if self.scripted is not None:
            return self.scripted()
        keys = pygame.key.get_pressed()
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        up = keys[pygame.K_w] or keys[pygame.K_UP]
        return PlayerInput(move_x=float(bool(right)) - float(bool(left)),
                           move_y=float(bool(down)) - float(bool(up)),
                           attack_held=bool(keys[pygame.K_SPACE]))
