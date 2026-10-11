"""Draws the battlefield. Reads simulation state; never modifies it."""
from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from entities.entity import Order, Team, Unit
from ui.effects import EffectsManager
from ui.widgets import Fonts, draw_bar, draw_text, health_color
from world.battlefield import Battlefield

GRASS = (62, 112, 56)
PLAYER_COLOR = (64, 112, 205)
ENEMY_COLOR = (192, 62, 56)
GENERAL_COLOR = (70, 96, 190)
GOLD = (236, 200, 80)


class BattleRenderer:
    def __init__(self, battlefield: Battlefield, effects: EffectsManager, fonts: Fonts) -> None:
        self.bf = battlefield
        self.effects = effects
        self.fonts = fonts
        self.background = self._build_background()

    # --- static background (built once) -------------------------------
    def _build_background(self) -> "pygame.Surface":
        w, h = int(self.bf.width), int(self.bf.height)
        surf = pygame.Surface((w, h))
        surf.fill(GRASS)
        rng = random.Random(self.bf.decoration_seed + 99)
        tile = 40
        for ty in range(0, h, tile):
            for tx in range(0, w, tile):
                shade = rng.randint(-7, 7)
                color = (GRASS[0] + shade, GRASS[1] + shade * 2, GRASS[2] + shade)
                pygame.draw.rect(surf, color, (tx, ty, tile, tile))
        for _ in range(260):  # grass tufts
            x, y = rng.randint(0, w), rng.randint(0, h)
            pygame.draw.line(surf, (48, 94, 44), (x, y), (x + 2, y - 5), 1)
            pygame.draw.line(surf, (74, 128, 66), (x + 3, y), (x + 4, y - 4), 1)
        for d in self.bf.decorations:
            self._draw_decoration(surf, d)
        return surf

    @staticmethod
    def _draw_decoration(surf: "pygame.Surface", d) -> None:
        x, y, s = int(d.x), int(d.y), int(d.size)
        if d.kind == "tree":
            pygame.draw.rect(surf, (96, 66, 38), (x - 3, y - 2, 6, s // 2 + 4))
            pygame.draw.circle(surf, (36, 88, 40), (x, y - s // 3), s)
            pygame.draw.circle(surf, (50, 110, 52), (x - s // 4, y - s // 2), int(s * 0.7))
        else:
            pts = [(x - s, y + s // 3), (x - s // 2, y - s // 2), (x + s // 3, y - s // 2), (x + s, y + s // 3)]
            pygame.draw.polygon(surf, (128, 128, 132), pts)
            pygame.draw.polygon(surf, (86, 86, 92), pts, 2)

    # --- per-frame drawing --------------------------------------------
    def draw(self, surface: "pygame.Surface") -> None:
        surface.blit(self.background, (0, 0))
        if self.bf.selected_target_id is not None:
            sel = self.bf.get_unit(self.bf.selected_target_id)
            if sel is not None:
                self._draw_selection(surface, sel)
        for unit in sorted(self.bf.units.values(), key=lambda u: u.y):
            self._draw_unit(surface, unit)
        self._draw_effects(surface)

    def _draw_selection(self, surface: "pygame.Surface", unit: Unit) -> None:
        x, y, r = int(unit.x), int(unit.y), int(unit.radius)
        pygame.draw.circle(surface, GOLD, (x, y), r + 6, 3)
        pygame.draw.polygon(surface, GOLD, [(x - 6, y - r - 26), (x + 6, y - r - 26), (x, y - r - 17)])

    def _draw_unit(self, surface: "pygame.Surface", unit: Unit) -> None:
        x, y, r = int(unit.x), int(unit.y), int(unit.radius)
        is_general = unit is self.bf.general
        if unit.team == Team.ENEMY:
            body = ENEMY_COLOR
        else:
            body = GENERAL_COLOR if is_general else PLAYER_COLOR
        pygame.draw.ellipse(surface, (30, 60, 30), (x - r, y + r // 2, r * 2, r))  # shadow

        # weapon line toward the current target (or forward when idle)
        target = self.bf.get_unit(unit.target_id)
        if target is not None:
            ang = math.atan2(target.y - unit.y, target.x - unit.x)
        else:
            ang = 0.0 if unit.team == Team.PLAYER else math.pi
        length = r + min(unit.stats.attack_range, 40) * 0.8
        end = (x + math.cos(ang) * length, y + math.sin(ang) * length)
        pygame.draw.line(surface, (210, 210, 214), (x, y), end, 3)

        pygame.draw.circle(surface, body, (x, y), r)
        pygame.draw.circle(surface, (16, 16, 20), (x, y), r, 2)
        if is_general:
            pygame.draw.circle(surface, GOLD, (x, y), r + 3, 2)
            crown = [(x - 7, y - r - 1), (x - 4, y - r - 8), (x, y - r - 2), (x + 4, y - r - 8), (x + 7, y - r - 1)]
            pygame.draw.polygon(surface, GOLD, crown)

        bar_w = 40 if is_general else 30
        bar = pygame.Rect(x - bar_w // 2, y - r - (20 if is_general else 14), bar_w, 5)
        draw_bar(surface, bar, unit.health_fraction, health_color(unit.health_fraction))

    def _draw_effects(self, surface: "pygame.Surface") -> None:
        font = self.fonts.get(22)
        for e in self.effects.effects:
            p = e.progress
            if e.kind == "swing":
                dx, dy = e.to_x - e.x, e.to_y - e.y
                d = math.hypot(dx, dy) or 1.0
                reach = min(d, 34)
                px, py = -dy / d, dx / d
                spread = 10 * (1 - p)
                for off in (-spread, spread):
                    a = (e.x + dx / d * 8 + px * off, e.y + dy / d * 8 + py * off)
                    b = (e.x + dx / d * reach, e.y + dy / d * reach)
                    pygame.draw.line(surface, (255, 244, 200), a, b, 3)
            elif e.kind == "damage":
                color = (255, 120, 110) if e.team == Team.PLAYER else (255, 240, 170)
                img = font.render(e.text, True, color)
                img.set_alpha(int(255 * (1 - p * p)))
                surface.blit(img, img.get_rect(center=(int(e.x), int(e.y - 26 * p))))
            elif e.kind == "puff":
                color = ENEMY_COLOR if e.team == Team.ENEMY else PLAYER_COLOR
                pygame.draw.circle(surface, color, (int(e.x), int(e.y)), int(e.size + 22 * p), 2)
