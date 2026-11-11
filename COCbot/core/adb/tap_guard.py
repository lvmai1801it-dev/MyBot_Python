"""Guard against accidental taps on the home-screen Shop button."""

from __future__ import annotations

from COCbot.core.config.coordinates import SHOP_BUTTON_BOX
from COCbot.core.ports import AdbPort, LoggerPort


def in_shop_zone(x: int, y: int, margin: int = 6) -> bool:
    """Return ``True`` when ``(x, y)`` overlaps the Shop hot zone."""
    try:
        px, py = int(x), int(y)
    except (TypeError, ValueError):
        return False
    return (
        (SHOP_BUTTON_BOX.x - margin) <= px <= (SHOP_BUTTON_BOX.right + margin)
        and (SHOP_BUTTON_BOX.y - margin) <= py <= (SHOP_BUTTON_BOX.bottom + margin)
    )


class TapGuard:
    """Reject taps that could open the Shop and break the farm loop."""

    def __init__(
        self,
        enabled: bool = True,
        margin: int = 6,
        logger: LoggerPort | None = None,
    ) -> None:
        """Create a guard with an optional logger."""
        self.enabled = enabled
        self.margin = margin
        self._logger = logger

    def blocked(self, x: int, y: int, context: str = "") -> bool:
        """Return ``True`` when the tap must be skipped."""
        if not self.enabled or not in_shop_zone(x, y, self.margin):
            return False
        where = f" [{context}]" if context else ""
        message = f"[GUARD] Skipped Shop tap at ({x},{y}){where}"
        if self._logger is not None:
            self._logger.warning(message)
        return True

    def tap(self, adb: AdbPort, x: int, y: int, context: str = "") -> bool:
        """Tap through *adb* unless the target is inside the Shop zone."""
        if self.blocked(x, y, context):
            return False
        return adb.tap(x, y)
