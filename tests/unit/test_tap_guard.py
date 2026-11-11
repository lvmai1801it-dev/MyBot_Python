"""Unit tests for the Shop tap guard."""

from __future__ import annotations

import unittest

from COCbot.core.adb.tap_guard import TapGuard, in_shop_zone
from COCbot.core.config.coordinates import SHOP_BUTTON_BOX


class FakeAdb:
    """Record taps without a device."""

    def __init__(self) -> None:
        self.taps: list[tuple[int, int]] = []

    def tap(self, x: int, y: int) -> bool:
        self.taps.append((x, y))
        return True


class TapGuardTests(unittest.TestCase):
    """Verify the Shop zone blocks only the dangerous taps."""

    def test_shop_zone(self) -> None:
        center = SHOP_BUTTON_BOX.center
        self.assertTrue(in_shop_zone(center.x, center.y))
        self.assertFalse(in_shop_zone(10, 10))

    def test_guard_blocks_shop_and_allows_other(self) -> None:
        adb = FakeAdb()
        guard = TapGuard()
        center = SHOP_BUTTON_BOX.center
        self.assertFalse(guard.tap(adb, center.x, center.y, "home"))
        self.assertTrue(guard.tap(adb, 100, 100, "home"))
        self.assertEqual(adb.taps, [(100, 100)])

    def test_disabled_guard_allows_everything(self) -> None:
        adb = FakeAdb()
        guard = TapGuard(enabled=False)
        center = SHOP_BUTTON_BOX.center
        self.assertTrue(guard.tap(adb, center.x, center.y))
        self.assertEqual(len(adb.taps), 1)


if __name__ == "__main__":
    unittest.main()
