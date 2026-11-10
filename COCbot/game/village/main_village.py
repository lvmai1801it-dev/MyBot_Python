# ==== COCbot/game/village/main_village.py ====
"""Entry checks for the Home Village (main village).

Flow used at bot start:
  1. Confirm the game is on the Home Village, not Builder Base / attack.
  2. Zoom out so the whole village is visible.
  3. Read the village's current Gold / Elixir / Dark Elixir.

Home Village is detected by the Shop/Build UI *and* the Dark Elixir bar.
Builder Base has no Dark Elixir bar, so the OCR region comes back empty.
"""

from __future__ import annotations

import os
import time

import cv2

import COCbot.app.paths  # noqa: F401
from COCbot.app import state
from COCbot.app.coords import HR_DE_REGION
from COCbot.app.paths import TEMPLATE_DIR
from COCbot.game.battle.ensure_home_base import ensure_home_base
from COCbot.game.village.home_routine import get_home_resources
from COCbot.game.village.zoom import multi_zoom_out
from COCbot.platform.unicode import imread_unicode
from COCbot.vision.capture import take_screenshot
from COCbot.vision.read_text.numbers import read_region

HOME_UI_TEMPLATES = ("shop.png", "build.png")
TEMPLATE_THRESHOLD = 0.80


def _match_template(gray, filename: str) -> bool:
    path = os.path.join(str(TEMPLATE_DIR), filename)
    tpl = imread_unicode(path, cv2.IMREAD_GRAYSCALE)
    if tpl is None or tpl.size == 0:
        return False
    if tpl.shape[0] > gray.shape[0] or tpl.shape[1] > gray.shape[1]:
        return False
    res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
    return float(res.max()) >= TEMPLATE_THRESHOLD


def is_main_village(img=None) -> bool:
    """True when the screenshot shows the Home Village UI."""
    if img is None:
        img = take_screenshot("main_village_check.png")
    if img is None or not getattr(img, "size", 0):
        print("[VILLAGE] Không chụp được màn hình để kiểm tra.")
        return False

    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    has_ui = any(_match_template(gray, name) for name in HOME_UI_TEMPLATES)
    dark_elixir = read_region(img, HR_DE_REGION)
    ok = has_ui and dark_elixir is not None

    print(
        f"[VILLAGE] Kiểm tra làng chính: home_ui={has_ui}, "
        f"dark_elixir={dark_elixir} -> {'ĐÚNG' if ok else 'KHÔNG PHẢI'}"
    )
    return ok


def read_current_resources() -> dict:
    """Read Gold / Elixir / Dark Elixir of the current Home Village."""
    gold, elixir, dark = get_home_resources()
    info = {
        "gold": int(gold or 0),
        "elixir": int(elixir or 0),
        "dark_elixir": int(dark or 0),
    }
    state.current_resources = info
    print(
        f"[VILLAGE] Tài nguyên hiện tại: "
        f"Gold={info['gold']:,} | Elixir={info['elixir']:,} | "
        f"DE={info['dark_elixir']:,}"
    )
    return info


def prepare_main_village(max_wait: int = 30) -> dict | None:
    """Confirm Home Village, zoom out, then read its resources.

    Returns the resource dict on success, or None when the game is not on the
    Home Village (or the bot was stopped while waiting).
    """
    deadline = time.time() + max(1, int(max_wait))
    confirmed = False

    while time.time() < deadline:
        if state.stop_event.is_set():
            return None
        state.pause_event.wait()
        if state.stop_event.is_set():
            return None

        if ensure_home_base():
            if is_main_village():
                confirmed = True
                break
            print("[VILLAGE] Có UI làng nhưng thiếu thanh Dark Elixir "
                  "→ có thể đang ở Builder Base.")
        time.sleep(2)

    if not confirmed:
        print("[VILLAGE] ❌ Không xác nhận được làng chính.")
        state.stop_event.set()
        return None

    print("[VILLAGE] ✅ Đang ở làng chính. Zoom out...")
    state.pause_event.wait()
    multi_zoom_out(state.host)
    time.sleep(0.8)

    return read_current_resources()
