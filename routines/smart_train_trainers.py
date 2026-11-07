# ==== routines/smart_train_trainers.py ====
import os
import time
import cv2
import subprocess
from typing import Tuple

import core.paths
from emulators.adb_config import ADB_BIN
from utils.screenshot_utils import take_screenshot
from utils.unicode import imread_unicode
from core.troop_registry import train_template_file

from routines.smart_train_utils import find_template_path, match, match_multiscale

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

# Vùng ROI chuẩn cho tab training (đã căn theo ảnh 860x732)
TRAIN_ROI = (5, 522, 857, 721)

def tap(pt: Tuple[int, int]):
    import main
    subprocess.run(
        [ADB_BIN, "-s", main.host, "shell", "input", "tap", str(pt[0]), str(pt[1])],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

def tap_icon_in_tab(tpl_name, count):
    full_shot = imread_unicode(take_screenshot(), cv2.IMREAD_COLOR)
    if full_shot is None:
        return False

    x1, y1, x2, y2 = TRAIN_ROI
    search_area = full_shot[y1:y2, x1:x2]

    path = find_template_path(tpl_name, subdir="Train_Tab")
    print(f"[TRAIN] Tìm '{tpl_name}' trong vùng ROI (folder: Train_Tab)")

    # 1. Thử match cơ bản
    ok, score, center = match(tpl_name, search_area, 0.65, subdir="Train_Tab")
    
    # 2. Nếu fail, thử multiscale
    if not ok:
        print(f"[TRAIN] Thử Multi-scale...")
        ok, score, center = match_multiscale(path, search_area, thresh=0.55)

    if not ok:
        print(f"[TRAIN] ❌ {tpl_name} not found (score={score:.3f})")
        return False

    tap_x = center[0] + x1
    tap_y = center[1] + y1
    print(f"[TRAIN] ✅ {tpl_name} tại ({tap_x}, {tap_y}) score={score:.3f}")

    for _ in range(count):
        tap((tap_x, tap_y))
        time.sleep(0.15)
    return True

def train_troops(recipe, counts, open_tab_coord, close_tab_coord):
    troops_needed = recipe.get("troops", {})
    if not troops_needed: return

    print(f"[TRAIN] Counts từ validate: {counts}")
    tap(open_tab_coord)
    time.sleep(1)

    failed = []
    for troop_name, expected in troops_needed.items():
        actual = counts.get(troop_name, 0)
        missing = max(0, expected - actual)
        if missing == 0:
            print(f"[TRAIN] ✅ {troop_name} đủ ({actual}/{expected})")
            continue

        print(f"[TRAIN] Cần thêm {missing}×{troop_name} (hiện {actual})")
        tpl_name = train_template_file(troop_name)
        if not tap_icon_in_tab(tpl_name, missing):
            failed.append(troop_name)

    tap(close_tab_coord)
    time.sleep(1)
    if failed:
        print(f"[TRAIN] ⚠ chưa train được: {failed}")

def train_spells(recipe, counts, open_tab_coord, close_tab_coord):
    spells_needed = recipe.get("spells", {})
    if not spells_needed: return

    tap(open_tab_coord)
    time.sleep(1)

    failed = []
    for spell_name, expected in spells_needed.items():
        actual = counts.get(spell_name, 0)
        missing = max(0, expected - actual)
        if missing == 0:
            print(f"[TRAIN] ✅ {spell_name} đủ ({actual}/{expected})")
            continue

        print(f"[TRAIN] Cần thêm {missing}×{spell_name} (hiện {actual})")
        tpl_name = train_template_file(spell_name, "spell")
        if not tap_icon_in_tab(tpl_name, missing):
            failed.append(spell_name)

    tap(close_tab_coord)
    time.sleep(1)
    if failed:
        print(f"[TRAIN] ⚠ chưa train được spell: {failed}")

def train_siege(recipe, open_tab_coord, close_tab_coord):
    siege_needed = recipe.get("siege", {})
    if not siege_needed: return

    tap(open_tab_coord)
    time.sleep(1)

    failed = []
    for siege_name, count in siege_needed.items():
        print(f"[TRAIN] {count}×{siege_name}")
        tpl_name = train_template_file(siege_name, "siege")
        if not tap_icon_in_tab(tpl_name, count):
            failed.append(siege_name)

    tap(close_tab_coord)
    time.sleep(1)
    if failed:
        print(f"[TRAIN] ⚠ chưa train được siege: {failed}")