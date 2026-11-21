"""Probe: does a uiautomator2 click reach the game on this emulator?

1. Return to the home village from wherever the game is.
2. u2 click the home Attack button -> measure the attack-menu pixel diff.
3. The same via the bot's AdbClient (`adb shell input tap`).
A large diff means the tap opened the menu and actually reached the game.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from COCbot.core.adb import AdbClient  # noqa: E402
from COCbot.core.config.coordinates import (  # noqa: E402
    NAV,
    SCOUT_SCREEN_REGION,
)
from COCbot.core.config.schema import AppConfig  # noqa: E402
from COCbot.core.vision import ScreenCapture, TemplateMatcher  # noqa: E402
from COCbot.core.vision.image import frame_image  # noqa: E402

ATTACK_BTN = (61, 648)
MENU_ROI = (0, 430, 860, 732)  # attack menu bottom sheet


def grab(capture) -> np.ndarray:
    frame = capture.capture()
    if frame is None:
        raise SystemExit("capture failed")
    return frame_image(frame)


def menu_diff(a, b) -> float:
    x1, y1, x2, y2 = MENU_ROI
    return float(cv2.absdiff(a[y1:y2, x1:x2], b[y1:y2, x1:x2]).mean())


def main() -> int:
    config = AppConfig()
    adb = AdbClient(host=config.emulator.host)
    if not adb.connect(config.emulator.host, timeout=5.0):
        raise SystemExit("ADB connect failed")
    capture = ScreenCapture(adb)
    matcher = TemplateMatcher()

    # --- 1. get back to the home village -------------------------------
    frame = capture.capture()
    if frame is None:
        raise SystemExit("capture failed")
    if matcher.match(frame, "end_battle.png", region=SCOUT_SCREEN_REGION, threshold=0.70):
        print("on the scout screen -> tapping Return Home")
        adb.tap(69, 595)
        time.sleep(4.0)
        frame = capture.capture()
        if frame is None:
            raise SystemExit("capture failed after return home")
    img = frame_image(frame)
    cv2.imwrite(str(ROOT / "artifacts" / "probe_home.png"), img)
    print(f"start frame saved (mean={img.mean():.1f})")

    # --- 2. uiautomator2 probe -----------------------------------------
    import uiautomator2 as u2  # noqa: E402

    dev = u2.connect(config.emulator.host)
    print(f"u2 window_size={dev.window_size()}")
    before = grab(capture)
    dev.click(*ATTACK_BTN)
    time.sleep(2.0)
    d_u2 = menu_diff(before, grab(capture))
    print(f"u2 click {ATTACK_BTN} -> menu diff = {d_u2:.2f}")
    adb.shell("input keyevent 4")  # BACK closes the menu either way
    time.sleep(2.0)

    # --- 3. adb input tap probe ----------------------------------------
    before = grab(capture)
    adb.tap(*ATTACK_BTN)
    time.sleep(2.0)
    d_adb = menu_diff(before, grab(capture))
    print(f"adb tap {ATTACK_BTN} -> menu diff = {d_adb:.2f}")
    adb.shell("input keyevent 4")
    time.sleep(1.5)

    print("\nverdict:")
    print(f"  uiautomator2 click : {'WORKS' if d_u2 > 8 else 'NO-OP (game did not react)'}")
    print(f"  adb input tap      : {'WORKS' if d_adb > 8 else 'NO-OP (game did not react)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
