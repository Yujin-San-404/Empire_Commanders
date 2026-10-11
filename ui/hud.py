"""Heads-up display and full-screen overlays. Reads state, issues no commands."""
from __future__ import annotations

from typing import Optional

import pygame

from entities.entity import Order
from ui.widgets import (BAD, GOOD, GOLD_TEXT, TEXT, TEXT_DIM, WARN, Fonts, draw_bar, draw_panel,
                        draw_text, health_color)
from world.battlefield import Battlefield, BattleResult


class Hud:
    def __init__(self, fonts: Fonts, width: int, height: int) -> None:
        self.fonts = fonts
        self.width = width
        self.height = height
        self.dim = pygame.Surface((width, height), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 150))

    def draw(self, surface: "pygame.Surface", bf: Battlefield, fps: Optional[float] = None) -> None:
        small, mid = self.fonts.get(24), self.fonts.get(30)

        # General + army (top-left)
        panel = pygame.Rect(12, 12, 320, 112)
        draw_panel(surface, panel)
        g = bf.general
        draw_text(surface, mid, "General", panel.x + 12, panel.y + 8)
        if g is not None:
            bar = pygame.Rect(panel.x + 100, panel.y + 11, 200, 16)
            draw_bar(surface, bar, g.health_fraction, health_color(g.health_fraction))
            draw_text(surface, small, f"{g.health:.0f}/{g.max_health:.0f}", bar.centerx, bar.y, TEXT, "center")
        soldiers = bf.allied_soldiers()
        fighting = sum(1 for s in soldiers if s.order == Order.ATTACK)
        following = sum(1 for s in soldiers if s.order == Order.FOLLOW)
        draw_text(surface, small, f"Army: {len(soldiers)} soldiers", panel.x + 12, panel.y + 40)
        draw_text(surface, small, f"Following {following}  |  Fighting {fighting}", panel.x + 12, panel.y + 62, TEXT_DIM)
        draw_text(surface, small, f"Enemies remaining: {len(bf.enemies())}", panel.x + 12, panel.y + 84,
                  BAD if bf.enemies() else GOOD)

        # Objective (top-centre)
        if bf.objective:
            w = 520
            op = pygame.Rect((self.width - w) // 2, 12, w, 52)
            draw_panel(surface, op)
            draw_text(surface, small, bf.title, op.centerx, op.y + 7, GOLD_TEXT, "center")
            draw_text(surface, small, bf.objective, op.centerx, op.y + 28, TEXT, "center")

        # Timer / FPS (top-right)
        minutes, seconds = divmod(int(bf.elapsed), 60)
        draw_text(surface, small, f"Time {minutes}:{seconds:02d}", self.width - 16, 16, TEXT, "right")
        if fps is not None:
            draw_text(surface, small, f"{fps:.0f} FPS", self.width - 16, 38, TEXT_DIM, "right")

        # Selected target (bottom-left)
        sel = bf.get_unit(bf.selected_target_id)
        if sel is not None:
            sp = pygame.Rect(12, self.height - 76, 260, 64)
            draw_panel(surface, sp)
            draw_text(surface, small, f"Target: {sel.stats.display_name}", sp.x + 12, sp.y + 8, GOLD_TEXT)
            bar = pygame.Rect(sp.x + 12, sp.y + 34, 170, 14)
            draw_bar(surface, bar, sel.health_fraction, health_color(sel.health_fraction))
            draw_text(surface, small, f"{sel.health:.0f}/{sel.max_health:.0f}", bar.right + 8, bar.y - 2, TEXT)

        # Controls hint (bottom-centre)
        hint = "WASD / Arrows: move   Space: attack   Click: select enemy   Esc: pause"
        draw_text(surface, small, hint, self.width // 2, self.height - 28, TEXT_DIM, "center")

    def draw_pause(self, surface: "pygame.Surface") -> None:
        surface.blit(self.dim, (0, 0))
        cx, cy = self.width // 2, self.height // 2
        draw_text(surface, self.fonts.get(96), "PAUSED", cx, cy - 90, TEXT, "center")
        draw_text(surface, self.fonts.get(32), "Esc: resume     R: restart battle     Q: quit", cx, cy + 10, TEXT_DIM, "center")

    def draw_result(self, surface: "pygame.Surface", bf: Battlefield) -> None:
        surface.blit(self.dim, (0, 0))
        cx, cy = self.width // 2, self.height // 2
        won = bf.result == BattleResult.VICTORY
        draw_text(surface, self.fonts.get(110), "VICTORY!" if won else "DEFEAT", cx, cy - 120,
                  GOOD if won else BAD, "center")
        minutes, seconds = divmod(int(bf.elapsed), 60)
        lines = [f"Enemies defeated: {bf.enemies_defeated}",
                 f"Soldiers lost: {bf.allies_lost}",
                 f"Battle time: {minutes}:{seconds:02d}"]
        for i, line in enumerate(lines):
            draw_text(surface, self.fonts.get(34), line, cx, cy - 20 + i * 36, TEXT, "center")
        draw_text(surface, self.fonts.get(32), "Enter: new battle     Q: quit", cx, cy + 120, TEXT_DIM, "center")
