"""Screen geometry and navigation coordinates.

Game-specific tap targets are declared as immutable points/rectangles here so
views and features never embed magic numbers. The current profile targets the
860x732 MEmu/LDPlayer window.
"""

from __future__ import annotations

from dataclasses import dataclass

from COCbot.models.geometry import Point, Rect, Size


@dataclass(frozen=True)
class ScreenConfig:
    """Reference screen size and helpers for converting rectangles."""

    size: Size = Size(860, 732)

    @property
    def width(self) -> int:
        """Return the reference screen width."""
        return self.size.width

    @property
    def height(self) -> int:
        """Return the reference screen height."""
        return self.size.height

    def point(self, x: int, y: int) -> Point:
        """Build a point on the reference screen."""
        return Point(x, y)

    def rect(self, x: int, y: int, width: int, height: int) -> Rect:
        """Build a rectangle on the reference screen."""
        return Rect(x, y, width, height)

    def bounds(self) -> Rect:
        """Return the full-screen rectangle."""
        return Rect(0, 0, self.width, self.height)

    def clamp(self, rect: Rect) -> Rect:
        """Clip *rect* to the reference screen."""
        return rect.clamp(self.bounds())

    def scale_point(self, point: Point, source: Size) -> Point:
        """Scale *point* from *source* resolution to the reference resolution."""
        if source.width <= 0 or source.height <= 0:
            return point
        return Point(
            round(point.x * self.width / source.width),
            round(point.y * self.height / source.height),
        )


SCREEN = ScreenConfig()


@dataclass(frozen=True)
class NavigationPoints:
    """Main-navigation tap targets shared by several features."""

    return_home: Point = Point(424, 625)
    battle_button: Point = Point(61, 648)
    find_match: Point = Point(155, 490)
    attack_confirm: Point = Point(728, 534)
    next_search: Point = Point(782, 597)
    menu: Point = Point(75, 493)
    treasure: Point = Point(147, 523)
    treasure_home: Point = Point(424, 611)


NAV = NavigationPoints()

# Regions intentionally kept in one place so vision code and tests agree.
SHOP_BUTTON_BOX = Rect(760, 315, 98, 105)
NEXT_BUTTON_REGION = Rect(692, 538, 163, 79)
SCOUT_SCREEN_REGION = Rect(10, 569, 118, 52)
BATTLE_REGION = Rect(340, 181, 192, 503)
STAR_REGIONS: tuple[Rect, ...] = (
    Rect(278, 73, 123, 184),
    Rect(360, 86, 138, 146),
    Rect(451, 78, 121, 180),
)
