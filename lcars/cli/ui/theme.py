"""LCARS visual theme constants."""

from __future__ import annotations

PANEL_ORANGE = "#f6a04d"
PANEL_ORANGE_DARK = "#d97a2b"
HEADER_PURPLE = "#b18cff"
VALUE_CYAN = "#78ddf0"
SUCCESS_GREEN = "#71d99e"
ERROR_RED = "#f07178"
TEXT_NEUTRAL = "#f5e6d3"
TEXT_MUTED = "#d4a06a"


def status_style(label: str) -> str:
    mapping = {
        "OPERATIONAL": SUCCESS_GREEN,
        "ONLINE": SUCCESS_GREEN,
        "OK": SUCCESS_GREEN,
        "STANDBY": VALUE_CYAN,
        "CONFIG REQUIRED": ERROR_RED,
        "OFFLINE": ERROR_RED,
        "FAIL": ERROR_RED,
        "WARN": PANEL_ORANGE,
    }
    return mapping.get(label.upper(), VALUE_CYAN)
