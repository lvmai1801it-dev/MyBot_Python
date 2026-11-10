"""Guard against accidental taps on the home-screen Shop button.

A stale coordinate or a template false-positive can land inside the Shop
button (right-middle of the 860x732 home screen). Opening the Shop leaves the
bot on the wrong screen and breaks every following step, so the home/training
tap paths call :func:`blocked` first.

Battle taps are intentionally NOT guarded: during an attack the Shop button is
not visible and the right edge is a valid deploy area.
"""

from __future__ import annotations

from COCbot.app.coords import SHOP_BUTTON_BOX


def in_shop_zone(x, y, margin: int = 6) -> bool:
    """True when (x, y) is inside (or very close to) the Shop button."""
    try:
        x, y = int(x), int(y)
    except (TypeError, ValueError):
        return False
    x1, y1, x2, y2 = SHOP_BUTTON_BOX
    return (x1 - margin) <= x <= (x2 + margin) and (y1 - margin) <= y <= (y2 + margin)


def blocked(x, y, context: str = "") -> bool:
    """Print and return True when the tap must be skipped."""
    if in_shop_zone(x, y):
        where = f" [{context}]" if context else ""
        print(f"[GUARD] Bo qua tap vao SHOP ({x},{y}){where}")
        return True
    return False
