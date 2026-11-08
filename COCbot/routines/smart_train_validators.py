# ==== routines/smart_train_validators.py ====
import os
import time
import cv2

import core.paths
from utils.screenshot_utils import take_screenshot
from utils.unicode import imread_unicode
from utils.ocr_reader import reader
from core.troop_registry import troop_icon_file, spell_icon_file, siege_icon_file

from routines.smart_train_ocr import read_number_ocr, read_troop_count
from routines.smart_train_utils import find_template_path, match, roi

BASE_DIR = str(core.paths.SRC_DIR)
TEMPLATE_ROOT = os.path.join(core.paths.TEMPLATE_DIR, "Smart_Auto_train")

SLOT_DATA = [
    ((380, 265, 439, 323), (382, 267, 412, 279)),
    ((442, 265, 501, 323), (443, 267, 474, 279)),
    ((503, 264, 564, 325), (506, 266, 536, 278)),
    ((568, 264, 624, 323), (569, 266, 598, 279)),
    ((628, 265, 688, 323), (631, 267, 657, 278)),
    ((692, 265, 750, 324), (693, 266, 721, 278)),
]

def _validate_army_window():
    debug_dir = os.path.join(BASE_DIR, "debug")
    os.makedirs(debug_dir, exist_ok=True)
    print("\n" + "="*50)
    print("[WINDOW CHECK] BẮT ĐẦU QUÁ TRÌNH DEBUG MỞ BẢNG ARMY")
    print("="*50)

    import main
    from core.coords import ST_BATTLE_BUTTON, ST_EDIT_ARMY_BUTTON, ST_ARMY_WINDOW_ROI
    from routines.smart_train_trainers import tap

    tap(ST_BATTLE_BUTTON)
    time.sleep(2)

    edit_btn_found = False
    for i in range(10):
        time.sleep(1)
        shot = imread_unicode(take_screenshot(), cv2.IMREAD_COLOR)
        if shot is None: continue
        
        path_edit = find_template_path("edit_army_btn", subdir="Smart_Auto_train")
        if path_edit:
            roi_search = roi(shot, 34, 678, 186, 729) 
            ok, score, center = match("edit_army_btn", roi_search, 0.7, subdir="Smart_Auto_train")
            if ok:
                print(f"[WINDOW CHECK] Đã thấy nút EDIT/ARMY (Score: {score:.2f})")
                edit_btn_found = True
                break
        else:
            if i >= 3:
                edit_btn_found = True
                break
    
    if not edit_btn_found:
        print("[WINDOW CHECK] ❌ Không tìm thấy nút EDIT/ARMY.")
        return False

    tap(ST_EDIT_ARMY_BUTTON)
    tpl_path = os.path.join(TEMPLATE_ROOT, "army_window.png")
    tpl = imread_unicode(tpl_path, cv2.IMREAD_COLOR)
    
    if tpl is None:
        print(f"[WINDOW CHECK] ❌ LỖI: Không đọc được ảnh mẫu {tpl_path}")
        return False

    for i in range(5):
        time.sleep(1)
        shot = imread_unicode(take_screenshot(), cv2.IMREAD_COLOR)
        if shot is None: continue
        
        army_roi = roi(shot, *ST_ARMY_WINDOW_ROI)
        if army_roi is None or army_roi.size == 0: continue
        if tpl.shape[0] > army_roi.shape[0] or tpl.shape[1] > army_roi.shape[1]: continue
            
        res = cv2.matchTemplate(army_roi, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        print(f"  -> [Lần {i+1}/5] score={max_val:.3f}")
        
        if max_val >= 0.6:
            print("[WINDOW CHECK] ✅ Đã mở được bảng Army thành công!")
            return True

    print("[WINDOW CHECK] ❌ Đã thử 5 lần nhưng không thấy bảng Army.")
    return False

def validate_troops(recipe):
    troops_needed = recipe.get("troops", {})
    if not troops_needed:
        return (True, {})

    debug_dir = os.path.join(BASE_DIR, "debug")
    os.makedirs(debug_dir, exist_ok=True)

    print("\n--- [VALIDATE TROOPS - QUÉT THEO 6 Ô CỐ ĐỊNH] ---")
    shot = imread_unicode(take_screenshot(), cv2.IMREAD_COLOR)
    if shot is None:
        return (False, {})

    found_troops = {}

    for i, (slot_box, num_box) in enumerate(SLOT_DATA):
        cell_img = roi(shot, *slot_box)
        if cell_img is None or cell_img.size == 0: continue

        detected_name = None
        for key in troops_needed:
            icon = troop_icon_file(key)
            path_tpl = find_template_path(icon, subdir="Army Troops")
            if not path_tpl: continue

            tpl = imread_unicode(path_tpl, cv2.IMREAD_COLOR)
            if tpl is None or tpl.shape[0] > cell_img.shape[0] or tpl.shape[1] > cell_img.shape[1]:
                continue

            res = cv2.matchTemplate(cell_img, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= 0.70:
                detected_name = key
                break

        if not detected_name: continue

        num_crop = roi(shot, *num_box)
        debug_prefix = os.path.join(debug_dir, f"slot_{i+1}_num")
        cv2.imwrite(f"{debug_prefix}_raw.png", num_crop)

        actual_count = read_number_ocr(num_crop)
        found_troops[detected_name] = actual_count
        print(f"[QUÉT] Ô {i+1}: {detected_name} (x{actual_count})")

    is_ok = True
    for key, expected in troops_needed.items():
        actual = found_troops.get(key, 0)
        if actual != expected:
            print(f"[VALIDATE] ❌ Sai {key}: Thực tế {actual} != Kỳ vọng {expected}")
            is_ok = False
        else:
            print(f"[VALIDATE] ✅ {key}: {actual} == {expected} (OK)")

    return (is_ok, found_troops)

def validate_spells(recipe, spell_roi, spell_space_roi):
    spells_needed = recipe.get("spells", {})
    if not spells_needed:
        return (True, {})

    shot = imread_unicode(take_screenshot(), cv2.IMREAD_COLOR)
    region = roi(shot, *spell_roi)

    for key in spells_needed:
        icon = spell_icon_file(key)
        ok, _, _ = match(icon, region, 0.92, subdir="Spells")
        if not ok:
            print(f"[VALIDATE] missing spell: {key}")
            return (False, {})

    frac_roi = roi(shot, *spell_space_roi)
    txts = reader.readtext(frac_roi, detail=0, paragraph=True)
    if not txts:
        return (False, {})
    
    raw = txts[0].replace(" ", "")
    if "/" not in raw:
        return (False, {})
        
    try:
        n, d = map(int, raw.split("/", 1))
        if n == 0 or n != d:
            return (False, {})
    except ValueError:
        return (False, {})

    found = {}
    for key, expected in spells_needed.items():
        icon = spell_icon_file(key)
        tpl_path = find_template_path(icon, subdir="Spells")
        if not tpl_path: continue
        
        tpl = imread_unicode(tpl_path, cv2.IMREAD_COLOR)
        if tpl is None: continue
        
        res = cv2.matchTemplate(region, tpl, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)
        actual = read_troop_count(region, max_loc, (tpl.shape[1], tpl.shape[0])) or 0
        found[key] = actual
        if actual != expected:
            print(f"[VALIDATE] {key}: {actual} != {expected}")
            return (False, found)

    return (True, found)

def validate_siege(recipe, siege_roi):
    siege_needed = recipe.get("siege", {})
    if not siege_needed:
        return True

    shot = imread_unicode(take_screenshot(), cv2.IMREAD_COLOR)
    region = roi(shot, *siege_roi)

    for key in siege_needed:
        icon = siege_icon_file(key)
        ok, _, _ = match(icon, region, 0.92, subdir="Siege Machines")
        if not ok:
            print(f"[VALIDATE] missing siege: {key}")
            return False

    return True