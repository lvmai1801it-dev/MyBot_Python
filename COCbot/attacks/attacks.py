import os
import cv2
import numpy as np
import math
import time
import random
import re
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
    import pytesseract
except ImportError:
    pytesseract = None

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

def check_slot_has_troops(img, slot_idx):
    """
    Kiểm tra xem slot có còn quân không (dựa vào badge màu xanh trên đầu thẻ).
    Trả về (has_troops: bool, remaining_count: int)
    """
    if img is None or img.size == 0:
        return False, 0

    slot_x = 30 + slot_idx * 72
    badge_roi = img[638:658, slot_x + 8:slot_x + 62]
    if badge_roi is None or badge_roi.size == 0:
        return False, 0

    mean_b, _mean_g, mean_r = cv2.mean(badge_roi)[:3]
    has_badge = (mean_b >= 85 and mean_b > mean_r + 15)
    if not has_badge:
        return False, 0

    # Đọc số lượng còn lại bằng Tesseract (nhanh ~5ms)
    rem = 0
    if pytesseract:
        try:
            white_mask = (badge_roi[:, :, 0] > 180) & (badge_roi[:, :, 1] > 180) & (badge_roi[:, :, 2] > 180)
            bin_img = np.zeros(badge_roi.shape[:2], dtype=np.uint8)
            bin_img[white_mask] = 255
            inv = 255 - bin_img
            padded = cv2.copyMakeBorder(inv, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
            padded = cv2.resize(padded, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
            txt = pytesseract.image_to_string(padded, config="--psm 7 -c tessedit_char_whitelist=xX0123456789").strip()
            digits = re.sub(r'\D', '', txt)
            if digits:
                rem = int(digits)
        except Exception:
            pass

    return True, rem if rem > 0 else 5

# ============================================================
# THUẬT TOÁN THẢ QUÂN RẢI ĐỀU NHIỀU ĐIỂM DỌC THEO CẠNH
# ============================================================
def get_spread_points_along_edge(edge, num_points=8):
    """
    Tạo danh sách các điểm rải đều dọc theo cạnh từ đầu đến cuối (thụt 5% ở 2 đầu để tránh góc mép).
    """
    if not edge or len(edge) < 2:
        return []
    p_start = edge[0]
    p_end = edge[-1]

    # Thụt vào 5% ở 2 đầu cạnh để tránh chạm viền góc
    sx = p_start[0] + (p_end[0] - p_start[0]) * 0.05
    sy = p_start[1] + (p_end[1] - p_start[1]) * 0.05
    ex = p_start[0] + (p_end[0] - p_start[0]) * 0.95
    ey = p_start[1] + (p_end[1] - p_start[1]) * 0.95

    if num_points <= 1:
        return [(int((sx + ex) / 2), int((sy + ey) / 2))]

    pts = []
    for i in range(num_points):
        ratio = i / (num_points - 1)
        px = int(sx + (ex - sx) * ratio)
        py = int(sy + (ey - sy) * ratio)
        pts.append((px, py))
    return pts

def drop_on_edge(edge, number, slots_per_edge=0, edge2=None):
    """
    Rải đều toàn bộ `number` lính qua NHIỀU ĐIỂM dọc theo cạnh (và edge2 nếu thả 2 hướng).
    """
    if number <= 0:
        return

    # Xác định số điểm rải đều: nếu có chỉ định thì dùng, không thì tự động 6 đến 12 điểm
    if slots_per_edge > 0:
        num_pts = slots_per_edge
    else:
        num_pts = max(6, min(12, number))

    pts1 = get_spread_points_along_edge(edge, num_pts)
    pts2 = get_spread_points_along_edge(edge2, num_pts) if edge2 else None

    nb_pts = len(pts1)
    troops_left = number

    for i in range(nb_pts):
        pts_remaining = nb_pts - i
        troops_at_point = round(troops_left / pts_remaining)

        p1 = pts1[i]
        p2 = pts2[i] if pts2 and i < len(pts2) else None

        for _ in range(troops_at_point):
            # Tap rải tại điểm trên hướng 1 (kèm micro-jitter +-3px)
            off_x = random.randint(-3, 3)
            off_y = random.randint(-3, 3)
            tap(p1[0] + off_x, p1[1] + off_y)

            # Tap rải tại điểm trên hướng 2 (kèm micro-jitter +-3px)
            if p2:
                off_x2 = random.randint(-3, 3)
                off_y2 = random.randint(-3, 3)
                tap(p2[0] + off_x2, p2[1] + off_y2)

            time.sleep(set_sleep(0))

        troops_left -= troops_at_point

def drop_on_edges(edges, nb_sides, number, slots_per_edge=0):
    """
    Phân bổ số quân trên số hướng mong muốn (1, 2, 3, hoặc 4 hướng) tại các điểm chỉ định.
    Khi nb_sides == 2: Thả tại các điểm xác định trên 2 hướng đối diện (Left & Right).
    """
    if number <= 0:
        return

    if nb_sides <= 0:
        nb_sides = 1

    troops_left = number
    if nb_sides >= 4:
        # 4 hướng: ghép cặp đối diện (Top-Bottom, Left-Right)
        for i in range(2):
            troops_per_edge = round(troops_left / (4 - i * 2))
            drop_on_edge(edges[i], troops_per_edge, slots_per_edge, edges[i + 2])
            troops_left -= troops_per_edge * 2
        return

    if nb_sides == 2:
        # 2 hướng: Thả rải đều trên 2 cạnh hình thoi Top-Left (edges[3]) và Bottom-Left (edges[2])
        troops_per_edge = round(troops_left / 2)
        drop_on_edge(edges[3], troops_per_edge, slots_per_edge, edges[2])
        return

    for i in range(nb_sides):
        if nb_sides == 1 or (nb_sides == 3 and i == 2):
            troops_per_edge = round(troops_left / (nb_sides - i))
            drop_on_edge(edges[i], troops_per_edge, slots_per_edge)
            troops_left -= troops_per_edge
        elif nb_sides == 3 and i != 1:
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
    # Thả Hero tại đỉnh Left (góc cánh tấn công chính)
    drop_point = edges[3][0]
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
    Xác định vùng thả quân hợp lệ theo chuẩn isometric của game:
    - Vùng biên ngoài (Viền VÀNG): Giới hạn tối đa có thể thả quân trên bản đồ 44x44.
    - Vùng biên trong (Redline ĐỎ): Viền ngoài cùng của cụm công trình nhà.
    - Vùng thả quân hợp lệ: Nằm giữa viền Vàng và Redline Đỏ (tỷ lệ an toàn ~35-40% từ Redline ra Vàng).
    Trả về 4 cạnh hình thoi (Top-Right, Bottom-Right, Bottom-Left, Top-Left),
    mỗi cạnh gồm 5 điểm chuẩn [(x0,y0), ..., (x4,y4)].
    """
    h, w = img_bgr.shape[:2]

    # 1. BIÊN NGOÀI HỢP LỆ (VIỀN VÀNG - MAP ISOMETRIC DIAMOND 44x44 DO USER ĐO)
    p_top_yellow = (435, 20)
    p_right_yellow = (860, 348)
    p_bottom_yellow = (436, 670)
    p_left_yellow = (8, 350)
    center_map = (433, 353)

    # 2. PHÁT HIỆN REDLINE NỘI BỘ (CỤM CÔNG TRÌNH NHÀ Ở TRUNG TÂM)
    b = img_bgr[:, :, 0].astype(int)
    g = img_bgr[:, :, 1].astype(int)
    r = img_bgr[:, :, 2].astype(int)

    # Vùng chứa làng (loại trừ hẳn rìa rừng, bãi biển và UI)
    village_roi = np.zeros((h, w), dtype=bool)
    village_roi[130:560, 150:760] = True

    # Màu đặc trưng của Redline / công trình nhà
    red_match = (r > g + 20) & (r > b + 35) & (r > 90) & village_roi
    ys, xs = np.where(red_match)

    if len(xs) > 20:
        # Tự động đo kích cỡ cụm nhà đối thủ quanh tâm (433, 353)
        dx = int(np.percentile(np.abs(xs - center_map[0]), 95))
        dy = int(np.percentile(np.abs(ys - center_map[1]), 95))
        dx = max(240, min(340, dx))
        dy = max(180, min(250, dy))
    else:
        dx = 280
        dy = 210

    # 4 đỉnh Redline đối xứng chuẩn isometric
    p_top_red = (center_map[0], center_map[1] - dy)
    p_bottom_red = (center_map[0], center_map[1] + dy)
    p_left_red = (center_map[0] - dx, center_map[1])
    p_right_red = (center_map[0] + dx, center_map[1])

    # 3. TẠO CÁC CẠNH THẢ QUÂN SONG SONG VỚI REDLINE, NẰM TRONG VÙNG VÀNG HỢP LỆ
    ui_bottom_limit = 615

    def parallel_offset(p1, p2, dist=40):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        L = math.hypot(dx, dy)
        if L == 0:
            return [p1, p1, p1, p1, p1]
        n1 = (-dy / L, dx / L)
        n2 = (dy / L, -dx / L)
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        to_mid = (mid[0] - center_map[0], mid[1] - center_map[1])
        n = n1 if (n1[0] * to_mid[0] + n1[1] * to_mid[1]) > (n2[0] * to_mid[0] + n2[1] * to_mid[1]) else n2

        op1 = (max(10, min(w - 10, int(p1[0] + n[0] * dist))), max(35, min(ui_bottom_limit, int(p1[1] + n[1] * dist))))
        op2 = (max(10, min(w - 10, int(p2[0] + n[0] * dist))), max(35, min(ui_bottom_limit, int(p2[1] + n[1] * dist))))

        return [
            op1,
            (int(op1[0] + (op2[0] - op1[0]) * 0.25), int(op1[1] + (op2[1] - op1[1]) * 0.25)),
            (int(op1[0] + (op2[0] - op1[0]) * 0.5),  int(op1[1] + (op2[1] - op1[1]) * 0.5)),
            (int(op1[0] + (op2[0] - op1[0]) * 0.75), int(op1[1] + (op2[1] - op1[1]) * 0.75)),
            op2
        ]

    # 4 cạnh hình thoi song song Redline, nằm hoàn toàn trong vùng hợp lệ
    return [
        parallel_offset(p_top_red, p_right_red, 40),    # Edge 0: Top-Right
        parallel_offset(p_right_red, p_bottom_red, 40), # Edge 1: Bottom-Right
        parallel_offset(p_bottom_red, p_left_red, 40),  # Edge 2: Bottom-Left
        parallel_offset(p_left_red, p_top_red, 40)     # Edge 3: Top-Left
    ]

def save_attack_debug_image(img, edges, nb_sides=2, out_name='redline_and_drop_points_debug.png'):
    """
    Vẽ trực quan khung Vàng, Redline Đỏ và các điểm thả quân của trận đánh thực tế ra ảnh debug.
    """
    try:
        dbg = img.copy()
        h, w = img.shape[:2]

        # 1. Viền VÀNG (Map Isometric Diamond 44x44)
        p_top_yellow = (435, 20)
        p_right_yellow = (860, 348)
        p_bottom_yellow = (436, 670)
        p_left_yellow = (8, 350)
        center_map = (433, 353)
        yellow_poly = np.array([p_top_yellow, p_right_yellow, p_bottom_yellow, p_left_yellow], dtype=np.int32)
        cv2.polylines(dbg, [yellow_poly], isClosed=True, color=(0, 255, 255), thickness=3)
        cv2.line(dbg, p_top_yellow, p_bottom_yellow, (0, 255, 255), 1)
        cv2.line(dbg, p_left_yellow, p_right_yellow, (0, 255, 255), 1)
        cv2.circle(dbg, center_map, 5, (0, 255, 255), -1)

        # 2. Viền ĐỎ (Redline nhà) - nối 4 đỉnh của các cạnh
        red_poly = np.array([edges[0][0], edges[1][0], edges[2][0], edges[3][0]], dtype=np.int32)
        cv2.polylines(dbg, [red_poly], isClosed=True, color=(0, 0, 255), thickness=3)

        # Overlay vùng hợp lệ (giữa Vàng và Đỏ)
        overlay = dbg.copy()
        cv2.fillPoly(overlay, [yellow_poly], (0, 255, 255))
        cv2.fillPoly(overlay, [red_poly], (0, 0, 0))
        cv2.addWeighted(overlay, 0.12, dbg, 0.88, 0, dbg)

        # 3. Vẽ các cạnh thả quân và điểm rải quân (Top-Left: Cyan, Bottom-Left: Green)
        tl_pts = get_spread_points_along_edge(edges[3], 8)
        bl_pts = get_spread_points_along_edge(edges[2], 8)

        cv2.line(dbg, edges[3][0], edges[3][-1], (255, 255, 0), 2)
        cv2.line(dbg, edges[2][0], edges[2][-1], (0, 255, 0), 2)

        for i, p in enumerate(tl_pts):
            cv2.circle(dbg, p, 5, (255, 255, 0), -1)
            cv2.putText(dbg, f'TL{i+1}', (p[0] - 15, p[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 0), 1)

        for i, p in enumerate(bl_pts):
            cv2.circle(dbg, p, 5, (0, 255, 0), -1)
            cv2.putText(dbg, f'BL{i+1}', (p[0] - 15, p[1] + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 0), 1)

        # Hero Drop
        hero_pt = ((edges[3][0][0] + edges[2][-1][0]) // 2, (edges[3][0][1] + edges[2][-1][1]) // 2)
        cv2.circle(dbg, hero_pt, 8, (255, 0, 255), -1)
        cv2.putText(dbg, 'HERO DROP', (hero_pt[0] - 40, hero_pt[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 2)

        cv2.rectangle(dbg, (10, 10), (620, 65), (0, 0, 0), -1)
        cv2.putText(dbg, 'DEBUG TRAN DANH: VI TRI THA QUAN (ISOMETRIC DIAMOND)', (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.putText(dbg, '- TL1..TL8 (Cyan) & BL1..BL8 (Green) | Hero (Tim)', (15, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 0), 1)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        debug_dir = os.path.join(base_dir, 'debug_attack')
        os.makedirs(debug_dir, exist_ok=True)
        out_file = os.path.join(debug_dir, out_name)
        cv2.imencode('.png', dbg)[1].tofile(out_file)
        print(f"[DEBUG] Da xuat anh debug tha quan: {out_file}")
    except Exception as e:
        print(f"[DEBUG ERROR] Khong the xuat anh debug: {e}")

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

    # Tự động xuất ảnh debug vị trí Redline và các điểm thả quân của trận này
    save_attack_debug_image(img, edges, nb_sides=cfg.get('sides', 2) if cfg else 2)

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

    # Thả quân theo thứ tự ưu tiên
    sorted_troops = sorted(atk_troops.values(), key=lambda t: get_priority(t['name']))

    for info in sorted_troops:
        if info.get('is_spell', False):
            continue  # Spells để thả sau

        troop_name = info['name']
        current_count = info.get('count', 0)
        if current_count <= 0:
            continue

        lname = troop_name.lower()
        if any(t in lname for t in ['giant', 'golem', 'pekka']):
            slots = 4 if current_count <= 10 else 6
        elif any(a in lname for a in ['dragon', 'electro_dragon', 'balloon']):
            slots = 6
        else:
            slots = 8  # Lính đông rải đều 8-10 điểm dọc theo cạnh

        # Thả quân và kiểm tra lại: còn quân thì thả tiếp, hết thì dừng
        for attempt in range(3):
            print(f"[ATTACK] Tha {current_count} {troop_name} (Slot {info['slot']}, lan {attempt + 1})...")
            select_drop_troop(info['slot'])
            time.sleep(0.15)

            drop_on_edges(edges, nb_sides, current_count, slots_per_edge=slots)
            time.sleep(0.3)

            # Chụp ảnh kiểm tra lại xem slot còn quân không
            verify_shot = take_screenshot('attack_verify.png')
            verify_img = imread_unicode(verify_shot, cv2.IMREAD_COLOR)
            if verify_img is None:
                break

            has_left, rem_count = check_slot_has_troops(verify_img, info['slot'])
            if not has_left or rem_count <= 0:
                print(f"[ATTACK] Slot {info['slot']} ({troop_name}) da het quan.")
                break
            else:
                print(f"[ATTACK] Slot {info['slot']} ({troop_name}) van con ~{rem_count} quan! Tha tiep...")
                current_count = rem_count

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
                select_drop_troop(info['slot'])
                time.sleep(0.2)
                mid_x = (edges[0][2][0] + edges[2][2][0]) // 2
                mid_y = (edges[0][2][1] + edges[2][2][1]) // 2
                for _ in range(count):
                    tap(mid_x + random.randint(-30, 30), mid_y + random.randint(-30, 30))
                    time.sleep(0.3)

    # Quét kiểm tra lại toàn bộ thanh quân lần cuối xem còn ô lính nào sót không
    final_shot = take_screenshot('attack_final_check.png')
    final_img = imread_unicode(final_shot, cv2.IMREAD_COLOR)
    if final_img is not None:
        for s_idx in range(11):
            has_left, rem = check_slot_has_troops(final_img, s_idx)
            if has_left and rem > 0:
                print(f"[ATTACK] Phat hien Slot {s_idx} con sot ~{rem} quan, tien hanh tha not...")
                select_drop_troop(s_idx)
                time.sleep(0.15)
                drop_on_edges(edges, nb_sides, rem, slots_per_edge=2)
                time.sleep(0.2)

    print("[ATTACK] === DA THA XONG ===")