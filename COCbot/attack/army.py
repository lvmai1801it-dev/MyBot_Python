import cv2
import os
import re
import sys
import numpy as np

# Đảm bảo console Windows không bị UnicodeEncodeError
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import pytesseract
except ImportError:
    pytesseract = None

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COCBOT_DIR = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.dirname(COCBOT_DIR)

# Cache templates
_TEMPLATES_CACHE = {}

def _norm_template(tpl):
    """Nếu template quá lớn so với slot (70x88), crop vùng trung tâm và resize về 42x42"""
    th, tw = tpl.shape[:2]
    if th > 55 or tw > 55:
        crop = tpl[int(th * 0.18):int(th * 0.80), int(tw * 0.18):int(tw * 0.82)]
        return cv2.resize(crop, (42, 42))
    return tpl

def _get_templates():
    if _TEMPLATES_CACHE:
        return _TEMPLATES_CACHE

    templates_dir = os.path.join(SRC_DIR, "Templates")

    # 1. Heroes
    hero_files = {
        'King': 'bk.png',
        'Queen': 'queen.png',
        'Warden': 'warden.png',
        'Champion': 'rc.png',
    }
    _TEMPLATES_CACHE['heroes'] = {}
    for hname, fname in hero_files.items():
        fpath = os.path.join(templates_dir, fname)
        if os.path.exists(fpath):
            img = cv2.imread(fpath, cv2.IMREAD_COLOR)
            if img is not None:
                _TEMPLATES_CACHE['heroes'][hname] = _norm_template(img)

    # 2. Army Troops
    _TEMPLATES_CACHE['troops'] = {}
    troops_dir = os.path.join(templates_dir, "Smart_Auto_train", "Army Troops")
    if os.path.isdir(troops_dir):
        for fname in os.listdir(troops_dir):
            if fname.lower().endswith(".png"):
                tname = os.path.splitext(fname)[0].capitalize()
                fpath = os.path.join(troops_dir, fname)
                img = cv2.imread(fpath, cv2.IMREAD_COLOR)
                if img is not None:
                    _TEMPLATES_CACHE['troops'][tname] = _norm_template(img)

    # 3. Spells
    _TEMPLATES_CACHE['spells'] = {}
    spells_dir = os.path.join(templates_dir, "Smart_Auto_train", "Spells")
    if os.path.isdir(spells_dir):
        for fname in os.listdir(spells_dir):
            if fname.lower().endswith(".png"):
                sname = os.path.splitext(fname)[0].capitalize()
                fpath = os.path.join(spells_dir, fname)
                img = cv2.imread(fpath, cv2.IMREAD_COLOR)
                if img is not None:
                    _TEMPLATES_CACHE['spells'][sname] = _norm_template(img)

    # 4. Siege & CC
    _TEMPLATES_CACHE['sieges'] = {}
    siege_dir = os.path.join(templates_dir, "Smart_Auto_train", "Siege Machines")
    if os.path.isdir(siege_dir):
        for fname in os.listdir(siege_dir):
            if fname.lower().endswith(".png"):
                sname = os.path.splitext(fname)[0].capitalize()
                fpath = os.path.join(siege_dir, fname)
                img = cv2.imread(fpath, cv2.IMREAD_COLOR)
                if img is not None:
                    _TEMPLATES_CACHE['sieges'][sname] = _norm_template(img)

    return _TEMPLATES_CACHE

# Bảng sửa lỗi OCR ký tự dễ nhầm lẫn
_OCR_CHAR_MAP = str.maketrans({
    'z': '2', 'Z': '2',
    'o': '0', 'O': '0',
    'I': '1', 'l': '1', '|': '1',
    's': '5', 'S': '5',
    'b': '6', 'B': '8'
})

def _read_quantity(img, x, y, w, h, slot_name="Unknown"):
    """Đọc số lượng lính từ badge góc trên của thẻ"""
    img_h, img_w = img.shape[:2]
    crop_y = max(0, y)
    crop_h = min(img_h - crop_y, h)
    crop_x = max(0, x)
    crop_w = min(img_w - crop_x, w)

    roi = img[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
    if roi.size == 0:
        return 0

    mean_b, _mean_g, mean_r = cv2.mean(roi)[:3]
    has_badge = (mean_b >= 80 and mean_b > mean_r + 15)

    # 1. Thử đọc bằng pytesseract (rất nhanh, lọc chữ trắng)
    if pytesseract:
        try:
            white_mask = (roi[:, :, 0] > 180) & (roi[:, :, 1] > 180) & (roi[:, :, 2] > 180)
            bin_img = np.zeros(roi.shape[:2], dtype=np.uint8)
            bin_img[white_mask] = 255
            inv = 255 - bin_img
            padded = cv2.copyMakeBorder(inv, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
            padded = cv2.resize(padded, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)

            text = pytesseract.image_to_string(padded, config="--psm 7 -c tessedit_char_whitelist=xX0123456789").strip()
            digits = re.sub(r'\D', '', text)
            if digits:
                num = int(digits)
                if num > 0:
                    print(f"  [OCR] {slot_name}: Tesseract read '{num}'")
                    return num
        except Exception:
            pass

    # 2. Thử đọc bằng EasyOCR (có map ký tự nhầm lẫn)
    try:
        from COCbot.vision.ocr import reader
        res = reader.readtext(roi, detail=0)
        if res:
            raw_text = "".join(res)
            mapped_text = raw_text.translate(_OCR_CHAR_MAP)
            digits = re.sub(r'\D', '', mapped_text)
            if digits:
                num = int(digits)
                print(f"  [OCR] {slot_name}: EasyOCR read '{num}' (raw: '{raw_text}')")
                return num
    except Exception:
        pass

    # 3. Fallback: Nếu có thẻ quân rõ ràng nhưng OCR không đọc ra
    if has_badge:
        print(f"  [OCR] {slot_name}: Co badge quan nhung OCR miss so -> Fallback 10")
        return 10

    return 0

def prepare_attack(img):
    """
    Quét thanh quân động cho mọi slot (tối đa 11 slots),
    nhận diện lính, hero, spell, CC.
    """
    print("[PREPARE] Dang quet thanh quan tran danh...")

    templates = _get_templates()
    atk_troops = {}
    heroes = {'King': -1, 'Queen': -1, 'Warden': -1, 'Champion': -1}
    cc_slot = -1

    img_h, img_w = img.shape[:2]
    # Thanh quân chuẩn 860x732: Y=638..726, slot X cách nhau 72px
    base_y = 638
    card_h = 88
    card_w = 70
    step_x = 72
    start_x = 30

    for idx in range(11):
        slot_x = start_x + idx * step_x
        if slot_x + card_w > img_w:
            break

        slot_roi = img[base_y:min(img_h, base_y + card_h), slot_x:min(img_w, slot_x + card_w)]
        if slot_roi.size == 0 or slot_roi.shape[0] < 50 or slot_roi.shape[1] < 50:
            continue

        tap_x = slot_x + (card_w // 2)
        tap_y = base_y + (card_h // 2)

        # 1. Kiểm tra Hero
        is_hero = False
        for hname, htpl in templates.get('heroes', {}).items():
            if htpl.shape[0] <= slot_roi.shape[0] and htpl.shape[1] <= slot_roi.shape[1]:
                res = cv2.matchTemplate(slot_roi, htpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= 0.55:
                    heroes[hname] = idx
                    is_hero = True
                    print(f"  [HERO] {hname} @ Slot {idx} (Score: {max_val:.2f})")
                    break
        if is_hero:
            continue

        # 2. Kiểm tra Siege Machine / Clan Castle
        is_siege = False
        for sname, stpl in templates.get('sieges', {}).items():
            if stpl.shape[0] <= slot_roi.shape[0] and stpl.shape[1] <= slot_roi.shape[1]:
                res = cv2.matchTemplate(slot_roi, stpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val >= 0.58:
                    cc_slot = idx
                    is_siege = True
                    print(f"  [SIEGE] {sname} @ Slot {idx} (Score: {max_val:.2f})")
                    break
        if is_siege:
            continue

        # 3. Kiểm tra dải màu xanh ở đầu thẻ (Y=638..658)
        badge_roi = img[638:658, slot_x + 8:slot_x + 62]
        has_badge = False
        if badge_roi.size > 0:
            mean_b, _mean_g, mean_r = cv2.mean(badge_roi)[:3]
            has_badge = (mean_b >= 85 and mean_b > mean_r + 15)

        # 4. Nhận diện Troop hoặc Spell
        best_name = None
        best_score = 0.0
        is_spell = False

        # Match Troop
        for tname, ttpl in templates.get('troops', {}).items():
            if ttpl.shape[0] <= slot_roi.shape[0] and ttpl.shape[1] <= slot_roi.shape[1]:
                res = cv2.matchTemplate(slot_roi, ttpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    best_name = tname

        # Match Spell
        for sname, stpl in templates.get('spells', {}).items():
            if stpl.shape[0] <= slot_roi.shape[0] and stpl.shape[1] <= slot_roi.shape[1]:
                res = cv2.matchTemplate(slot_roi, stpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    best_name = sname
                    is_spell = True

        # Bỏ qua ô trống: phải có badge hoặc score cao (>= 0.70)
        if not has_badge and best_score < 0.70:
            continue

        # Đặt tên thẻ
        slot_name = best_name if (best_score >= 0.50 and best_name) else f"Troop_{idx}"

        # Đọc số lượng
        qty_x = slot_x + 8
        qty_y = 638
        qty_w = 54
        qty_h = 20
        count = _read_quantity(img, qty_x, qty_y, qty_w, qty_h, slot_name=slot_name)

        if count > 0 or has_badge:
            actual_count = count if count > 0 else 10
            # Key theo slot index để tránh trùng lặp đè mất thẻ cùng loại
            key = f"{slot_name}_{idx}"
            atk_troops[key] = {
                'slot': idx,
                'name': slot_name,
                'count': actual_count,
                'tap_x': tap_x,
                'tap_y': tap_y,
                'is_spell': is_spell,
                'match_score': best_score
            }
            print(f"  [OK] {slot_name}: x{actual_count} @ Slot {idx} ({tap_x}, {tap_y}) [Score: {best_score:.2f}]")

    return atk_troops, heroes, cc_slot