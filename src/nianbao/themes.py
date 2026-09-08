"""Card themes — 网易云-style dark gradient palettes.

Each theme is a flat set of RGB tuples consumed by :mod:`nianbao.cards`.
Three themes ship with v0.1; premium theme packs are a v0.2 plan item.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    bg_top: tuple[int, int, int]
    bg_bottom: tuple[int, int, int]
    accent: tuple[int, int, int]
    accent_soft: tuple[int, int, int]
    text: tuple[int, int, int]
    text_dim: tuple[int, int, int]
    heat_low: tuple[int, int, int]
    heat_high: tuple[int, int, int]

    @property
    def attribution(self) -> str:
        return f"{self.label} · 由 Nianbao 生成"


THEMES: dict[str, Theme] = {
    "midnight": Theme(
        name="midnight",
        label="Midnight",
        bg_top=(26, 27, 58),
        bg_bottom=(12, 12, 28),
        accent=(225, 62, 62),        # 网易云红
        accent_soft=(255, 122, 110),
        text=(245, 245, 250),
        text_dim=(158, 158, 180),
        heat_low=(44, 46, 86),
        heat_high=(225, 62, 62),
    ),
    "aurora": Theme(
        name="aurora",
        label="Aurora",
        bg_top=(13, 43, 48),
        bg_bottom=(8, 20, 30),
        accent=(64, 224, 174),
        accent_soft=(130, 245, 200),
        text=(240, 250, 248),
        text_dim=(140, 170, 170),
        heat_low=(30, 62, 66),
        heat_high=(64, 224, 174),
    ),
    "sunset": Theme(
        name="sunset",
        label="Sunset",
        bg_top=(58, 24, 56),
        bg_bottom=(24, 10, 34),
        accent=(255, 148, 92),
        accent_soft=(255, 190, 140),
        text=(252, 244, 248),
        text_dim=(176, 148, 172),
        heat_low=(70, 34, 68),
        heat_high=(255, 148, 92),
    ),
}

DEFAULT_THEME = "midnight"


def get_theme(name: str | None) -> Theme:
    """Look up a theme by name; unknown names fall back to the default."""
    return THEMES.get(name or DEFAULT_THEME, THEMES[DEFAULT_THEME])
