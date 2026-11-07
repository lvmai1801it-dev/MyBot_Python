# ==== attacks/attacks.py ====
import cv2
import numpy as np
import time
import math

from utils.screenshot_utils import take_screenshot
from utils.unicode import imread_unicode
from adb_utils import tap  # Dùng hàm tap từ adb_utils bạn vừa tách

# ============================================================
# XỬ LÝ MÀU REDLINE
# ============================================================
def hex_to_bgr(hex_color):
    """Chuyển mã màu Hex sang BGR"""
    hex_color = hex_color.lstrip('#')
    b = int(hex_color[4:6], 16)
    g = int(hex_color[2:4], 16)
    r = int(hex_color[0:2], 16)
    return (b, g, r)

def get_redline_drop_points(img_bgr, tolerance=25):
    """
    Quét màu đỏ/cam của Redline, gom cụm và trả về danh sách các tọa độ thả quân.
    tolerance=25 để bù trừ nhiễu render của game (có thể tăng lên 30 nếu không tìm thấy).
    """
    img_int = img_bgr.astype(np.int16)
    final_mask = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    
    # Bảng màu đỏ/cam của Redline
    target_hex_colors = [
        "#cb6326", "#d56e2a", "#cf6425", "#7c3f16",
        "#bd4f1c", "#da6226", "#c04e1f",
    ]
    
    for hex_color in target_hex_colors:
        target_bgr = hex_to_bgr(hex_color)
        diff = np.abs(img_int - np.array(target_bgr, dtype=np.int16))
        color_match_mask = np.all(diff <= tolerance, axis=-1)
        final_mask[color_match_mask] = 255

    # Làm dày các nét đứt (nếu có) để dễ gom cụm
    kernel = np.ones((5, 5), np.uint8)
    final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel)
    final_mask = cv2.dilate(final_mask, kernel, iterations=1)

    # Tìm các đường viền (cụm pixel)
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    drop_points = []
    h, w = img_bgr.shape[:2]
    
    for cnt in contours:
        # Bỏ qua các nhiễu rác quá nhỏ (dưới 20 pixel vuông)
        if cv2.contourArea(cnt) < 20:
            continue
            
        # Lấy tâm của cụm màu
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            # Chỉ lấy những điểm nằm trong vùng thả quân (tránh vùng UI ở dưới đáy)
            # Tọa độ Y phải nhỏ hơn (chiều cao màn hình - 180) để không tap vào thanh chọn quân
            if cY < h - 180 and cY > 50:
                # Lọc: Nếu điểm này quá sát điểm trước đó (< 35px) thì bỏ qua
                # Giúp bot thả quân dàn đều dọc theo đường line chứ không bị dồn cục
                is_too_close = False
                for (px, py) in drop_points:
                    if math.hypot(cX - px, cY - py) < 35:
                        is_too_close = True
                        break
                
                if not is_too_close:
                    drop_points.append((cX, cY))
                    
    # Sắp xếp các điểm từ trái sang phải để thả quân mượt hơn
    drop_points.sort(key=lambda p: p[0])
    return drop_points


# ============================================================
# HÀM ATTACK CHÍNH
# ============================================================
def run_attack(cfg):
    print("[ATTACK] Bắt đầu quét Redline...")
    
    # 1. Chụp ảnh màn hình chuẩn bị đánh
    shot_path = take_screenshot('attack_redline.png')
    img = imread_unicode(shot_path, cv2.IMREAD_COLOR)
    if img is None:
        print("❌ Không chụp được màn hình game!")
        return

    # 2. Lấy danh sách các điểm thả quân dọc Redline
    points = get_redline_drop_points(img, tolerance=25)
    print(f"[ATTACK] Tìm thấy {len(points)} điểm thả quân dọc Redline.")
    
    if not points:
        print("⚠️ Không tìm thấy Redline, dùng Fallback thả 4 góc màn hình.")
        h, w = img.shape[:2]
        points = [(100, 100), (w-100, 100), (100, h-250), (w-100, h-250)]

    # 3. Chọn quân (Bạn có thể sửa lại tọa độ này theo độ phân giải của bạn)
    # Ví dụ: Nút chọn Rồng/Lính nằm ở góc dưới bên trái (X=80, Y=650)
    TROOP_BTN_X, TROOP_BTN_Y = 80, 650 
    print(f"  👉 Chọn quân tại ({TROOP_BTN_X}, {TROOP_BTN_Y})")
    tap(TROOP_BTN_X, TROOP_BTN_Y)
    time.sleep(0.3)

    # 4. Thả quân dọc Redline
    print("[ATTACK] Bắt đầu thả quân dọc Redline...")
    for i, (x, y) in enumerate(points):
        print(f"  -> Thả quân tại ({x}, {y})")
        tap(x, y)
        time.sleep(0.15) # Delay nhẹ 0.15s để game kịp nhận diện

    # 5. Thả Spells / Heroes (Tùy chọn)
    print("[ATTACK] Đã thả xong quân dọc Redline.")
    
    # Nếu bạn muốn thả spell (VD: Rage ở giữa), thêm code vào đây:
    # tap(SPELL_BTN_X, SPELL_BTN_Y)
    # tap(CENTER_X, CENTER_Y)
    
    time.sleep(1.0)