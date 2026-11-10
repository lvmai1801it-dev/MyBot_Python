# ==== COCbot/game/training/smart_train.py ====
import time

import cv2

from COCbot.app.coords import (
    ST_CLOSE_ARMY_TAB,
    ST_CLOSE_ARMY_WINDOW,
    ST_CLOSE_SIEGE_TAB,
    ST_CLOSE_SPELL_TAB,
    ST_OPEN_ARMY_TAB,
    ST_OPEN_SIEGE_TAB,
    ST_OPEN_SPELL_TAB,
    ST_SIEGE_ROI,
    ST_SPELL_ROI,
    ST_SPELL_SPACE_ROI,
)
from COCbot.game.training.smart_train_trainers import (
    tap,
    train_siege,
    train_spells,
    train_troops,
)
from COCbot.game.training.smart_train_validators import (
    _validate_army_window,
    validate_siege,
    validate_spells,
    validate_troops,
)
from COCbot.platform.unicode import imread_unicode
from COCbot.vision.capture import take_screenshot
from COCbot.vision.ocr import reader


def smart_train(cfg):
    recipe = cfg.get("recipe")
    if not recipe:
        try:
            from COCbot.app.army_presets import get_active_preset
            name, preset = get_active_preset()
            if preset and any([preset.get("troops"), preset.get("spells"), preset.get("siege")]):
                print(f"[SMART] Không có recipe trong cfg -> dùng preset '{name}'")
                recipe = preset
        except Exception as e:
            print(f"[SMART] Không đọc được preset: {e}")

    if not recipe or not any([recipe.get("troops"), recipe.get("spells"), recipe.get("siege")]):
        print("[SMART] ❌ No recipe configured")
        return

    print(f"[SMART] Recipe: {cfg.get('recipe_name', '?')}")

    if not _validate_army_window():
        print("[SMART] Army window not detected")
        return

    # --- VALIDATE ---
    army_ok, army_counts = validate_troops(recipe)
    spell_ok, spell_counts = validate_spells(recipe, ST_SPELL_ROI, ST_SPELL_SPACE_ROI)
    siege_ok = validate_siege(recipe, ST_SIEGE_ROI)

    if army_ok and spell_ok and siege_ok:
        print("[SMART] ✅ All valid")
        _ensure_close_army_window()   # ← Gọi hàm đóng có verify
        return

    # --- TRAIN (Chỉ train phần thiếu) ---
    if not army_ok:
        train_troops(recipe, army_counts, ST_OPEN_ARMY_TAB, ST_CLOSE_ARMY_TAB)
    if not spell_ok:
        train_spells(recipe, spell_counts, ST_OPEN_SPELL_TAB, ST_CLOSE_SPELL_TAB)
    if not siege_ok:
        train_siege(recipe, ST_OPEN_SIEGE_TAB, ST_CLOSE_SIEGE_TAB)

    _ensure_close_army_window()


def _ensure_close_army_window(max_attempts=3):
    """
    Đóng Army window và VERIFY đã về màn hình chính.
    Retry tối đa max_attempts lần nếu chưa đóng được.
    """
 
    
    for attempt in range(1, max_attempts + 1):
        # 1. Tap nút X
        tap(ST_CLOSE_ARMY_WINDOW)
        time.sleep(1.0)   # Chờ animation đóng
        
        # 2. Verify: chụp lại, check header có còn không
        try:
            shot_path = take_screenshot('smart_train_close_verify')
            img = imread_unicode(shot_path, cv2.IMREAD_COLOR)
            if img is None:
                continue
            
            # Cắt vùng header của Army window (thanh MY ARMY / SAVED RECIPES / COOKBOOK)
            h, w = img.shape[:2]
            # Header nằm ở khoảng y 55-85, x 75-750 trên giả lập 860x732
            crop = img[55:85, 75:750]
            results = reader.readtext(crop, detail=0)
            header = ' '.join(results).upper()
            
            still_open = any(k in header for k in ['MY ARMY', 'SAVED RECIPES', 'COOKBOOK'])
            
            if not still_open:
                print(f"[SMART] ✅ Army window đã đóng thành công (lần {attempt})")
                return True
            else:
                print(f"[SMART] ⚠️ Army window vẫn mở (lần {attempt}), tap lại X...")
        except Exception as e:
            print(f"[SMART] Lỗi verify đóng window: {e}")
    
    print(f"[SMART] ❌ Không đóng được Army window sau {max_attempts} lần thử!")
    return False