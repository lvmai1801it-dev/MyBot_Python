"""Centralized game coordinates for 860×732 resolution.
Toàn bộ tọa độ đã được hardcode (gán cứng) chuẩn xác cho màn hình 860x732.
Không sử dụng bất kỳ hệ số scale nào.
"""

SCREEN_W = 860
SCREEN_H = 732


_SX = 1.0
_SY = 1.0

# Hàm tự động chuyển từ X, Y, Width, Height sang X1, Y1, X2, Y2
def R(x, y, w, h):
    return (x, y, x + w, y + h)

# ═══════════════════════════════════════════════════════════
# main.py — general navigation
# ═══════════════════════════════════════════════════════════
# Total screen (860x732). The home-screen Shop button lives here; no bot
# routine needs to tap it, so tap_guard blocks accidental taps.
SHOP_BUTTON_BOX = (760, 315, 858, 420)

RETURN_HOME_TAP = (424, 625)
BATTLE_BUTTON_TAP = (61, 648)
FIND_MATCH_TAP = (155, 490)
ATTACK_CONFIRM_TAP = (728, 534)
NEXT_SEARCH_TAP = (782, 597)
MENU_TAP = (75, 493)
TREASURE_TAP = (147, 523)
TREASURE_HOME_TAP = (424, 611)

# ── next button / scout / battle detection ────────────────
NEXT_BTN_REGION = (692, 538, 855, 617)
SCOUT_SCREEN_ROI = (10, 569, 128, 621)
BATTLE_ROI = (340, 181, 532, 684)

# ── star detection ────────────────────────────────────────
STAR1_ROI = (278, 73, 401, 257)
STAR2_ROI = (360, 86, 498, 232)
STAR3_ROI = (451, 78, 572, 258)

# ── resource gain OCR ─────────────────────────────────────
GAIN_GOLD_L = (315, 303, 443, 342)
GAIN_ELIXIR_L = (317, 350, 444, 392)
GAIN_DE_L = (346, 398, 444, 438)
GAIN_GOLD_R = (544, 361, 632, 399)
GAIN_ELIXIR_R = (546, 401, 632, 437)
GAIN_DE_R = (557, 440, 632, 475)

# ── hammer / treasure region ──────────────────────────────
HAMMER_REGION = (334, 577, 518, 658)

# ═══════════════════════════════════════════════════════════
# main.py — Clan Capital
# ═══════════════════════════════════════════════════════════
CC_SCENERY_ROI = (81, 163, 694, 723)
CC_V1_ROI = (1, 86, 86, 200)
CC_V2_ROI = (1, 141, 106, 727)
CC_START_ROI = (762, 538, 856, 607)
CC_HOME_TAP = (56, 650)
CC_AVAIL_ATKS_ROI = (774, 552, 820, 589)
CC_ENEMY_SWIPE = (445, 223, 445, 89, 500)
CC_ENEMY_TAP = (802, 657)
CC_CLOSE_PANEL = (132, 213)
CC_VILLAGE_STAR_ROI = (212, 599, 360, 659)
CC_VILLAGE_AVAIL_ROI = (440, 605, 584, 707)
CC_ARMY_WINDOW_TAP = (506, 654)
CC_TROOPS_ROI = (72, 150, 109, 203)
CC_SPELLS_ROI = (72, 344, 107, 391)
CC_ATTACK_READY_ROI = (3, 511, 124, 589)
CC_ATTACK_TAP = (702, 417)
CC_REINITIATE_TAP = (523, 473)
CC_FULL_GOLD_ROI = (207, 159, 671, 588)
CC_PANEL_ROI = (40, 587, 806, 729)
CC_CAPITAL_SWIPE = (390, 467, 381, 157, 1000)

CC_VILLAGE_COORDS = {
    'Goblin Mines':        (571, 588),
    'Skeleton Park':       (383, 588),
    'Golem Quarry':        (210, 538),
    'Balloon Lagoon':      (313, 419),
    "Builder's Workshop":  (491, 447),
    'Dragon Cliffs':       (610, 376),
    'Wizard Valley':       (412, 274),
    'Barbarian Camp':      (529, 205),
    'Capital Peak':        (408, 68),
}

CC_TROOP_DROPPOINTS = {
    'Balloon Lagoon':      (405, 446),
    'Barbarian Camp':      (448, 423),
    "Builder's Workshop":  (467, 318),
    'Dragon Cliffs':       (455, 336),
    'Goblin Mines':        (377, 516),
    'Golem Quarry':        (428, 368),
    'Skeleton Park':       (484, 311),
    'Wizard Valley':       (551, 230),
    'Capital Peak':        (408, 68),
}

CC_SPELL_DROPPOINTS = {
    'Balloon Lagoon':      [(171, 480), (162, 176), (259, 290)],
    'Barbarian Camp':      [(362, 232), (318, 181)],
    "Builder's Workshop":  [(307, 352), (467, 193)],
    'Dragon Cliffs':       [(449, 205), (325, 136)],
    'Goblin Mines':        [(348, 318), (170, 351)],
    'Golem Quarry':        [(234, 300), (342, 186)],
    'Skeleton Park':       [(451, 160), (362, 258)],
    'Wizard Valley':       [(490, 118), (355, 186), (149, 260)],
}

CP_FIRST_DROPPOINTS = [(427, 361), (433, 351)]

# polygon for glow detection (relative coordinates, resolution-independent)
CP_GLOW_POLY_REL = [
    (0.63125, 0.09555555555555556),
    (0.751875, 0.26555555555555554),
    (0.339375, 0.81),
    (0.19125, 0.6422222222222222),
]

BRIGHT_EDGE_ROI_RAW = (126, 171, 833, 587)
GLOW_TL = (833, 587)
GLOW_BR = (126, 171)

# ═══════════════════════════════════════════════════════════
# boot_recovery.py
# ═══════════════════════════════════════════════════════════
BOOT_DISMISS_TAP = (430, 120)

# ═══════════════════════════════════════════════════════════
# home_routine.py — wall upgrades
# ═══════════════════════════════════════════════════════════
HR_GOLD_REGION = (660, 12, 828, 46)
HR_ELIXIR_REGION = (660, 45, 828, 80)
HR_DE_REGION = (660, 79, 828, 114)
HR_VALIDATE_REGION = (337, 465, 527, 506)
HR_POPUP_REGION = (276, 28, 610, 72)
HR_DISMISS_COORD = (614, 170)
HR_GOLD_UPGRADE = (0, 575)
HR_ELIXIR_UPGRADE = (0, 571)
HR_CONFIRM_UPGRADE = (599, 636)
HR_WALL_ROI = (145, 81, 720, 638)
HR_HOME_TAP = (397, 29)
HR_SWIPE_START = (435, 527)
HR_SWIPE_END = (435, 94)
HR_VALIDATION_ROI = (126, 456, 761, 705)
HR_SAFE_TAP = (227, 55)
HR_CLOSE_TAP = (661, 20)
HR_RETRY_SWIPE_START = (525, 128)
HR_RETRY_SWIPE_END = (537, 351)

# ═══════════════════════════════════════════════════════════
# IsTarget.py — enemy resource OCR
# ═══════════════════════════════════════════════════════════
RES_GOLD_ROI = (21, 65, 102, 29)
RES_ELIXIR_ROI = (20, 92, 107, 33)
RES_DE_ROI = (21, 121, 97, 30)

# ═══════════════════════════════════════════════════════════
# quick_train.py
# ═══════════════════════════════════════════════════════════
QT_CLOSE_ARMY_WINDOW = (791, 185)
QT_ARMY_RECIPE_PANE = (418, 73)
QT_ROI_ARMY1 = (733, 154, 846, 346)
QT_ROI_ARMY2 = (735, 395, 845, 598)
QT_CONFIRM_TAP = (523, 475)

# ═══════════════════════════════════════════════════════════
# smart_train.py
# ═══════════════════════════════════════════════════════════
ST_ARMY_ROI = R(375, 254, 804, 333)
ST_SPELL_ROI = R(376, 362, 649, 438)
ST_SIEGE_ROI = R(654, 364, 805, 440)
ST_SPACE_ROI = R(377, 237, 461, 259)
ST_SPELL_SPACE_ROI = R(375, 344, 445, 368)

ST_TRASH_ARMY_ROI = R(784, 241, 800, 258)
ST_TRASH_SPELL_ROI = R(627, 350, 644, 365)
ST_TRASH_SIEGE_ROI = R(785, 350, 805, 368)

ST_TAP_CLEAR_ARMY = (831, 170)
ST_TAP_CLEAR_SPELL = (658, 349)
ST_TAP_CLEAR_SIEGE = (830, 347)
ST_CONFIRM_TAP_ARMY = (521, 471)
ST_CONFIRM_TAP_SPELL = (526, 474)
ST_CONFIRM_TAP_SIEGE = (519, 473)

ST_OPEN_ARMY_TAB = (666, 300)
ST_CLOSE_ARMY_TAB = (321, 232)
ST_OPEN_SPELL_TAB = (540, 400)
ST_CLOSE_SPELL_TAB =(321, 232)
ST_OPEN_SIEGE_TAB = (730, 400)
ST_CLOSE_SIEGE_TAB = (321, 232)
ST_CLOSE_ARMY_WINDOW = (791, 185)

ST_BATTLE_BUTTON = (61, 648) # Nút Attack
ST_EDIT_ARMY_BUTTON = (67, 704) # Nút Edit/Army ở góc dưới trái

# ⭐ TỌA ĐỘ BẠN VỪA CẮT: X=74, Y=169, W=245, H=42
ST_ARMY_WINDOW_ROI = (74, 169, 319, 211)
ST_SPACE_SECONDARY_ROI = (404, 149, 461, 187)

# ═══════════════════════════════════════════════════════════
# requests.py — xin quân qua Clan Chat (UI hiện tại)
# ═══════════════════════════════════════════════════════════
RT_CHAT_OPEN_TAP = (60, 368)        # nút shield + bong bóng chat (trái màn hình home)
RT_CHAT_WAR_CLOSE_TAP = (607, 238)  # X của popup "Clan War / Join War"
RT_CHAT_REQUEST_TAP = (320, 700)    # icon lâu đài (Clan Castle) ở footer chat
RT_CHAT_REQUEST_SEND = (538, 467)   # nút Send trong hộp Request Reinforcements
RT_CHAT_REQUEST_CANCEL = (300, 467)
RT_CHAT_EXIT_CANCEL = (300, 443)    # Cancel của hộp "Confirm Exit"
RT_WAR_POPUP_ROI = (465, 300, 690, 420)
RT_REQUEST_DIALOG_ROI = (170, 105, 690, 165)
RT_CHAT_FOOTER_ROI = (20, 675, 240, 725)
RT_EXIT_DIALOG_ROI = (250, 190, 650, 275)

# ═══════════════════════════════════════════════════════════
# clan_games.py
# ═══════════════════════════════════════════════════════════
CG_OPEN_EVENTS_TAP = (190, 675)
CG_EVENTS_WINDOW_ROI = (325, 7, 558, 102)
CG_SEARCH_ROI = (119, 20, 748, 721)
CG_SWIPE_1 = ('523', '542', '527', '109', '2000')   
CG_SWIPE_2 = ('366', '663', '366', '136', '1000')
CG_CLOSE_TAP_1 = (764, 45)
CG_CLOSE_TAP_2 = (710, 53)
CG_CLOSE_TAP_3 = (762, 47)
CG_FINISHED_ROI = (68, 598, 261, 709)
CG_BUSY_ROI = (299, 117, 430, 342)
CG_OPEN_REGION_OFFSETS = (-97, -137, 538, 106)

# ═══════════════════════════════════════════════════════════
# detect_home_base.py — ALREADY PORTED (kept as reference)
# ═══════════════════════════════════════════════════════════
DHB_SETTINGS_ROI = (777, 406, 859, 576)
DHB_OCR_ROI_1 = (779, 350, 852, 464)
DHB_OCR_ROI_2 = (757, 672, 850, 721)