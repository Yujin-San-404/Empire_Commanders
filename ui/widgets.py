"""Small drawing helpers shared by the HUD and renderer (rendering only)."""
from __future__ import annotations

from typing import Dict, Tuple

import pygame

Color = Tuple[int, int, int]

TEXT = (240, 236, 224)
TEXT_DIM = (170, 168, 160)
PANEL_BG = (24, 26, 32)
PANEL_BORDER = (92, 86, 70)
GOOD = (88, 190, 96)
WARN = (222, 190, 70)
BAD = (205, 70, 62)
GOLD_TEXT = (236, 200, 80)


class Fonts:
    """Caches pygame's built-in default font by size (no font files required)."""

    def __init__(self) -> None:
        self._cache: Dict[int, "pygame.font.Font"] = {}

    def get(self, size: int) -> "pygame.font.Font":
        if size not in self._cache:
            self._cache[size] = pygame.font.Font(None, size)
        return self._cache[size]


def draw_text(surface: "pygame.Surface", font: "pygame.font.Font", text: str, x: int, y: int,
              color: Color = TEXT, align: str = "left") -> "pygame.Rect":
    img = font.render(text, True, color)
    rect = img.get_rect()
    if align == "center":
        rect.midtop = (x, y)
    elif align == "right":
        rect.topright = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


def draw_panel(surface: "pygame.Surface", rect: "pygame.Rect") -> None:
    pygame.draw.rect(surface, PANEL_BG, rect, border_radius=6)
    pygame.draw.rect(surface, PANEL_BORDER, rect, width=2, border_radius=6)


def health_color(fraction: float) -> Color:
    if fraction > 0.6:
        return GOOD
    if fraction > 0.3:
        return WARN
    return BAD


def draw_bar(surface: "pygame.Surface", rect: "pygame.Rect", fraction: float,
             color: Color = GOOD) -> None:
    fraction = max(0.0, min(1.0, fraction))
    pygame.draw.rect(surface, (60, 24, 24), rect)
    if fraction > 0:
        fill = pygame.Rect(rect.x, rect.y, max(1, int(rect.w * fraction)), rect.h)
        pygame.draw.rect(surface, color, fill)
    pygame.draw.rect(surface, (10, 10, 12), rect, width=1)
