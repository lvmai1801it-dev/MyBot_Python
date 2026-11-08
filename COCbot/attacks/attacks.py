import cv2
import numpy as np
import math
import time
import random
import sys

# Đảm bảo console Windows không bị lỗi UnicodeEncodeError khi log
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None

try:
    from COCbot.core import state
    from COCbot.emulator.adb_utils import _get_target_device, tap as adb_tap
    from COCbot.utils.screenshot_utils import take_screenshot
    from COCbot.utils.unicode import imread_unicode
    from COCbot.attacks.PrepareAttack import prepare_attack
except ImportError:
    import state
    from emulator.adb_utils import _get_target_device, tap as adb_tap
    from utils.screenshot_utils import take_screenshot
    from utils.unicode import imread_unicode

# ============================================================
# ĐIỀU KHIỂN TAP TỐC ĐỘ CAO (ƯU TIÊN U2, FALLBACK ADB_TAP)
# ============================================================
_device = None
_device_host = None

def get_device():
    """Lấy uiautomator2 instance cho host hiện tại để tap tốc độ cao"""
    global _device, _device_host
    if not u2:
        return None
    try:
        host = _get_target_device()
    except Exception:
        host = getattr(state, 'host', None)
    if not host:
        return None
    if _device is not None and _device_host == host:
        return _device
    try:
        _device = u2.connect(host)
        _device_host = host
    except Exception:
        _device = None
    return _device

def tap(x, y, delay=0.02):
    """
    Tap tọa độ: đầu tiên qua uiautomator2 (siêu nhanh), fallback về adb_tap.
    """
    x, y = int(x), int(y)
    dev = get_device()
    if dev:
        try:
            dev.click(x, y)
            if delay:
                time.sleep(delay)
            return True
        except Exception:
            pass

    try:
        adb_tap(x, y)
        if delay:
            time.sleep(delay)
        return True
    except Exception as e:
        print(f"[TAP ERROR] {e}")
        return False

# ============================================================
# CẤU HÌNH TỌA ĐỘ VÀ TIỆN ÍCH
# ============================================================
def set_sleep(sleep_type):
    if sleep_type == 0:
        return random.randint(1, 10) * 0.01
    return random.randint(1, 10) * 0.1

def select_drop_troop(slot_idx):
    """Click chọn ô lính / hero / spell ở thanh quân dưới màn hình"""
    if slot_idx < 0 or slot_idx > 10:
        return False
    x = 30 + slot_idx * 72 + 35
    y = 682
    tap(x, y)
    time.sleep(0.15)
    return True

# ============================================================
# THUẬT TOÁN THẢ QUÂN
# ============================================================
def drop_on_edge(edge, number, slots_per_edge=0, edge2=None):
    """
    Thả toàn bộ `number` lính lên cạnh (và edge2 đối diện nếu có).
    Mỗi vị trí slot sẽ tap đúng số lượng lính phân bổ.
    """
    if number <= 0:
        return

    if slots_per_edge == 0 or number < slots_per_edge:
        slots_per_edge = number

    if slots_per_edge == 1:
        for _ in range(number):
            tap(edge[2][0], edge[2][1])
            if edge2:
                tap(edge2[2][0], edge2[2][1])
            time.sleep(set_sleep(0))
    elif slots_per_edge == 2:
        t1 = math.ceil(number / 2)
        t2 = number - t1
        for _ in range(t1):
            tap(edge[1][0], edge[1][1])
            if edge2:
                tap(edge2[1][0], edge2[1][1])
            time.sleep(set_sleep(0))
        for _ in range(t2):
            tap(edge[3][0], edge[3][1])
            if edge2:
                tap(edge2[3][0], edge2[3][1])
            time.sleep(set_sleep(0))
    else:
        min_x, max_x = edge[0][0], edge[4][0]
        min_y, max_y = edge[0][1], edge[4][1]
        if edge2:
            min_x2, max_x2 = edge2[0][0], edge2[4][0]
            min_y2, max_y2 = edge2[0][1], edge2[4][1]

        troops_left = number
        for i in range(slots_per_edge):
            troops_per_slot = round(troops_left / (slots_per_edge - i))
            denom = max(1, slots_per_edge - 1)
            pos_x = min_x + ((max_x - min_x) * i) / denom
            pos_y = min_y + ((max_y - min_y) * i) / denom

            for _ in range(troops_per_slot):
                tap(round(pos_x), round(pos_y))
                if edge2:
                    pos_x2 = max_x2 - ((max_x2 - min_x2) * i) / denom
                    pos_y2 = max_y2 - ((max_y2 - min_y2) * i) / denom
                    tap(round(pos_x2), round(pos_y2))
                time.sleep(set_sleep(0))

            troops_left -= troops_per_slot

def drop_on_edges(edges, nb_sides, number, slots_per_edge=0):
    """Phân bổ số quân trên số cạnh mong muốn (1, 2, 3, hoặc 4 cạnh)"""
    if number <= 0:
        return

    if nb_sides <= 0:
        nb_sides = 1

    troops_left = number
    if nb_sides >= 4:
        # 4 cạnh: chia cặp cạnh đối xứng (Top-Bottom, Left-Right)
        for i in range(2):
            troops_per_edge = round(troops_left / (4 - i * 2))
            drop_on_edge(edges[i], troops_per_edge, slots_per_edge, edges[i + 2])
            troops_left -= troops_per_edge * 2
        return

    for i in range(nb_sides):
        if nb_sides == 1 or (nb_sides == 3 and i == 2):
            troops_per_edge = round(troops_left / (nb_sides - i))
            drop_on_edge(edges[i], troops_per_edge, slots_per_edge)
            troops_left -= troops_per_edge
        elif (nb_sides == 2 and i == 0) or (nb_sides == 3 and i != 1):
            troops_per_edge = round(troops_left / (nb_sides - i * 2))
            drop_on_edge(edges[i + 3], troops_per_edge, slots_per_edge, edges[i + 1])
            troops_left -= troops_per_edge * 2

# ============================================================
# THẢ HEROES
# ============================================================
def drop_heroes_v2(_img, edges, hero_slots):
    if not hero_slots:
        return False

    print("[ATTACK] Bat dau tha Heroes...")
    drop_point = edges[0][2]
    hero_order = ['King', 'Queen', 'Warden', 'Champion', 'Prince']
    dropped_any = False

    for hero_name in hero_order:
        slot_idx = hero_slots.get(hero_name, -1)
        if slot_idx is not None and slot_idx >= 0:
            print(f"  -> Tha {hero_name} (Slot {slot_idx})")
            select_drop_troop(slot_idx)
            time.sleep(0.2)

            tap_x = drop_point[0] + random.randint(-5, 5)
            tap_y = drop_point[1] + random.randint(-5, 5)
            tap(tap_x, tap_y)
            time.sleep(0.3)
            dropped_any = True

    return dropped_any

# ============================================================
# CẤU HÌNH MÀU REDLINE (Đỏ/Cam)
# ============================================================
TARGET_HEX_COLORS = [
    "#cb6326", "#d56e2a", "#cf6425", "#7c3f16",
    "#bd4f1c", "#da6226", "#c04e1f"
]

def hex_to_bgr(hex_color):
    """Chuyển mã màu Hex sang BGR của OpenCV"""
    hex_color = hex_color.lstrip('#')
    b = int(hex_color[4:6], 16)
    g = int(hex_color[2:4], 16)
    r = int(hex_color[0:2], 16)
    return (b, g, r)

def get_redline_edges(img_bgr, tolerance=25):
    """
    Quét màu đỏ/cam của Redline, gom cụm và trả về 4 cạnh (Top, Right, Bottom, Left).
    Mỗi cạnh là một mảng gồm 5 điểm [(x0,y0), (x1,y1), ..., (x4,y4)].
    """
    img_int = img_bgr.astype(np.int16)
    final_mask = np.zeros(img_bgr.shape[:2], dtype=np.uint8)

    for hex_color in TARGET_HEX_COLORS:
        target_bgr = hex_to_bgr(hex_color)
        diff = np.abs(img_int - np.array(target_bgr, dtype=np.int16))
        color_match_mask = np.all(diff <= tolerance, axis=-1)
        final_mask[color_match_mask] = 255

    kernel = np.ones((5, 5), np.uint8)
    final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel)
    final_mask = cv2.dilate(final_mask, kernel, iterations=1)

    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    points = []
    h, w = img_bgr.shape[:2]

    for cnt in contours:
        if cv2.contourArea(cnt) < 20:
            continue

        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])

            if 50 < cY < h - 180 and not any(math.hypot(cX - px, cY - py) < 35 for (px, py) in points):
                points.append((cX, cY))

    points.sort(key=lambda p: p[0])

    if not points:
        print("[WARN] Khong tim thay Redline, dung Fallback 4 goc man hinh.")
        return [
            [(100, 100), (200, 100), (300, 100), (400, 100), (500, 100)],
            [(w - 100, 100), (w - 100, 200), (w - 100, 300), (w - 100, 400), (w - 100, 500)],
            [(w - 100, h - 250), (w - 200, h - 250), (w - 300, h - 250), (w - 400, h - 250), (w - 500, h - 250)],
            [(100, h - 250), (100, h - 350), (100, h - 450), (100, h - 550), (100, h - 650)]
        ]

    # Thêm margin 15px để đảm bảo điểm thả quân luôn nằm ngoài Redline
    margin = 15
    min_x = max(10, min(p[0] for p in points) - margin)
    max_x = min(w - 10, max(p[0] for p in points) + margin)
    min_y = max(60, min(p[1] for p in points) - margin)
    max_y = min(h - 180, max(p[1] for p in points) + margin)

    def make_edge(p1, p2):
        return [
            p1,
            (int(p1[0] + (p2[0] - p1[0]) * 0.25), int(p1[1] + (p2[1] - p1[1]) * 0.25)),
            (int(p1[0] + (p2[0] - p1[0]) * 0.5),  int(p1[1] + (p2[1] - p1[1]) * 0.5)),
            (int(p1[0] + (p2[0] - p1[0]) * 0.75), int(p1[1] + (p2[1] - p1[1]) * 0.75)),
            p2
        ]

    return [
        make_edge((min_x, min_y), (max_x, min_y)),
        make_edge((max_x, min_y), (max_x, max_y)),
        make_edge((max_x, max_y), (min_x, max_y)),
        make_edge((min_x, max_y), (min_x, min_y))
    ]

# ============================================================
# HÀM THỰC THI CHÍNH
# ============================================================
def run_attack(cfg):
    print("[ATTACK] === BAT DAU TRAN DANH ===")

    # Kiểm tra tránh chụp lúc màn hình chuyển cảnh (mây trắng)
    img = None
    for attempt in range(5):
        shot_path = take_screenshot('attack_redline.png')
        img = imread_unicode(shot_path, cv2.IMREAD_COLOR)
        if img is None:
            time.sleep(0.5)
            continue
        if img.mean() > 220:
            print("[ATTACK] Dang trong hieu ung may trang, cho 1s...")
            time.sleep(1.0)
            continue
        break

    if img is None:
        print("[ERROR] Khong chup duoc man hinh!")
        return

    edges = get_redline_edges(img)
    if not edges:
        print("[ERROR] Khong tim thay Redline, huy danh!")
        return

    atk_troops, heroes_slots, cc_slot = prepare_attack(img)

    has_troops = bool(atk_troops)
    has_heroes = bool(heroes_slots and any(v >= 0 for v in heroes_slots.values()))
    if not has_troops and not has_heroes:
        print("[ERROR] Khong co quan hoac hero nao tren thanh! Huy danh.")
        return

    nb_sides = cfg.get('sides', 2) if cfg else 2

    # Phân loại thứ tự thả quân thông minh:
    # 1. Tanks / meat shields đi trước
    tanks = ['golem', 'ice_golem', 'giant', 'pekka', 'root_rider', 'barbarian', 'valkyrie']
    # 2. Main damage / không quân / quái đông
    main_attack = ['dragon', 'electro_dragon', 'baby_dragon', 'dragon_rider', 'balloon', 'wizard', 'witch', 'bowler', 'miner', 'hog_rider', 'archer', 'minion']

    def get_priority(name):
        lname = name.lower()
        for idx, t in enumerate(tanks):
            if t in lname:
                return (0, idx)
        for idx, m in enumerate(main_attack):
            if m in lname:
                return (1, idx)
        return (2, 0)

    # Thả quân theo thứ tự ưu tiên (duyệt qua values để không bị mất các slot trùng tên lính)
    sorted_troops = sorted(atk_troops.values(), key=lambda t: get_priority(t['name']))

    for info in sorted_troops:
        if info.get('is_spell', False):
            continue  # Spells để thả sau

        count = info.get('count', 0)
        troop_name = info['name']
        if count <= 0:
            continue

        print(f"[ATTACK] Tha {count} {troop_name} (Slot {info['slot']})...")
        tap(info['tap_x'], info['tap_y'])
        time.sleep(0.2)

        lname = troop_name.lower()
        if any(t in lname for t in ['giant', 'golem', 'pekka']):
            slots = 1 if count <= 10 else 2
        elif any(a in lname for a in ['dragon', 'electro_dragon', 'balloon']):
            slots = 2 if nb_sides <= 2 else 0
        else:
            slots = 0

        drop_on_edges(edges, nb_sides, count, slots_per_edge=slots)
        time.sleep(set_sleep(0))

    # Thả Heroes
    if has_heroes:
        drop_heroes_v2(img, edges, heroes_slots)

    # Thả Clan Castle / Siege Machine nếu có
    if cc_slot >= 0:
        print(f"[ATTACK] Tha Clan Castle / Siege (Slot {cc_slot})...")
        select_drop_troop(cc_slot)
        time.sleep(0.2)
        tap(edges[0][2][0], edges[0][2][1])
        time.sleep(0.3)

    # Thả Spells nếu có
    for info in sorted_troops:
        if info.get('is_spell', False):
            count = info.get('count', 0)
            spell_name = info['name']
            if count > 0:
                print(f"[ATTACK] Tha Spell {spell_name} (x{count})...")
                tap(info['tap_x'], info['tap_y'])
                time.sleep(0.2)
                mid_x = (edges[0][2][0] + edges[2][2][0]) // 2
                mid_y = (edges[0][2][1] + edges[2][2][1]) // 2
                for _ in range(count):
                    tap(mid_x + random.randint(-30, 30), mid_y + random.randint(-30, 30))
                    time.sleep(0.3)

    print("[ATTACK] === DA THA XONG ===")