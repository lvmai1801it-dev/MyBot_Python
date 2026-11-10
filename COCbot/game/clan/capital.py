# ==== COCbot/game/clan/capital.py ====
from __future__ import annotations

import math
import os
import random
import time

import cv2
import numpy as np

import COCbot.app.paths  # noqa: F401
from COCbot.app.config import (
    CC_DIR_SPELLS,
    CC_DIR_TROOPS,
    CC_THRESH_PCT,
    CC_TPL_AVAILABLE_ATKS,
    CC_TPL_ENEMY_LAND,
    CC_TPL_FULL_GOLD_WINDOW,
    CC_TPL_TROOPS_READY,
    CC_TPL_VILLAGE_3STAR,
    CC_TPL_VILLAGE_AVAIL,
    CC_TROOP_TAP_COUNTS,
    CC_VILLAGE_ORDER,
    CLAN_CAPITAL_CACHE,
    CLAN_CAPITAL_DIR,
    CLAN_CAPITAL_SCENERY_DIR,
    CLAN_CAPITAL_THRESH,
    CP_FRESH_TEMPLATE,
    CP_FRESH_THRESHOLD,
    DROP_SPACING,
)
from COCbot.app.coords import (
    CC_ARMY_WINDOW_TAP,
    CC_ATTACK_READY_ROI,
    CC_ATTACK_TAP,
    CC_AVAIL_ATKS_ROI,
    CC_CAPITAL_SWIPE,
    CC_CLOSE_PANEL,
    CC_ENEMY_SWIPE,
    CC_ENEMY_TAP,
    CC_FULL_GOLD_ROI,
    CC_HOME_TAP,
    CC_PANEL_ROI,
    CC_REINITIATE_TAP,
    CC_SCENERY_ROI,
    CC_SPELL_DROPPOINTS,
    CC_SPELLS_ROI,
    CC_START_ROI,
    CC_TROOP_DROPPOINTS,
    CC_TROOPS_ROI,
    CC_V1_ROI,
    CC_V2_ROI,
    CC_VILLAGE_AVAIL_ROI,
    CC_VILLAGE_COORDS,
    CC_VILLAGE_STAR_ROI,
    CP_FIRST_DROPPOINTS,
    CP_GLOW_POLY_REL,
    GLOW_BR,
    GLOW_TL,
    MENU_TAP,
)
from COCbot.app.state import pause_event
from COCbot.game.account.boot_recovery import boot_recovery
from COCbot.game.battle.ensure_home_base import ensure_home_base
from COCbot.platform.adb_utils import run_adb, tap
from COCbot.platform.unicode import imread_unicode
from COCbot.vision.capture import take_screenshot
from COCbot.vision.templates import _match_color, _match_gray

CLAN_CAPITAL_ROI = CC_SCENERY_ROI


# ---------- geometry helpers ----------
def _sorted_box(tl, br):
    x1, x2 = sorted([tl[0], br[0]])
    y1, y2 = sorted([tl[1], br[1]])
    return x1, y1, x2, y2


def _points_along(x1, y1, x2, y2, spacing=DROP_SPACING):
    L = math.hypot(x2 - x1, y2 - y1)
    if L < spacing:
        return [((x1 + x2) // 2, (y1 + y2) // 2)]
    n = int(L // spacing) + 1
    return [
        (int(round(x1 + (i + 0.5) / n * (x2 - x1))),
         int(round(y1 + (i + 0.5) / n * (y2 - y1))))
        for i in range(n)
    ]


def _abs_poly_from_rel(img_shape, poly_rel):
    H, W = img_shape[:2]
    return [(int(px * W), int(py * H)) for px, py in poly_rel]


def get_glow_drop_points_poly(img_bgr, poly_abs, spacing=DROP_SPACING):
    if not poly_abs:
        return get_glow_drop_points(img_bgr, spacing=spacing)
    xs = [p[0] for p in poly_abs]
    ys = [p[1] for p in poly_abs]
    x1, y1 = max(0, min(xs)), max(0, min(ys))
    x2, y2 = min(img_bgr.shape[1] - 1, max(xs)), min(img_bgr.shape[0] - 1, max(ys))
    if x2 <= x1 or y2 <= y1:
        return [(sum(xs) // 4, sum(ys) // 4)]
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return [(sum(xs) // 4, sum(ys) // 4)]
    poly_roi = [(px - x1, py - y1) for px, py in poly_abs]
    mask = np.zeros(roi.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [np.array(poly_roi, dtype=np.int32)], 255)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    _, Sc, Vc = cv2.split(hsv)
    white_mask = ((Sc < 80) & (Vc > 220)).astype(np.uint8) * 255
    white_mask = cv2.bitwise_and(white_mask, mask)
    white_mask = cv2.morphologyEx(
        white_mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=2
    )
    white_mask = cv2.dilate(white_mask, np.ones((3, 3), np.uint8), iterations=1)
    edges = cv2.Canny(white_mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, math.pi / 180, 60, minLineLength=90, maxLineGap=12)
    if lines is None:
        return [(sum(xs) // 4, sum(ys) // 4)]
    segs = sorted([tuple(map(int, l[0])) for l in lines],
                  key=lambda L: math.hypot(L[2] - L[0], L[3] - L[1]), reverse=True)[:6]
    pts = []
    for xa, ya, xb, yb in segs:
        pts.extend(_points_along(xa + x1, ya + y1, xb + x1, yb + y1, spacing))
    out = []
    for px, py in pts:
        if all(abs(px - qx) > 18 or abs(py - qy) > 18 for qx, qy in out):
            out.append((px, py))
    return out[:12]


def get_glow_drop_points(img_bgr, tl=GLOW_TL, br=GLOW_BR, spacing=DROP_SPACING):
    H, W = img_bgr.shape[:2]
    x1, y1, x2, y2 = _sorted_box(tl, br)
    x1, x2 = max(0, min(W - 1, x1)), max(0, min(W, x2))
    y1, y2 = max(0, min(H - 1, y1)), max(0, min(H, y2))
    if x2 <= x1 or y2 <= y1:
        return [((tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2)]
    roi = img_bgr[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    _, Sc, Vc = cv2.split(hsv)
    mask = ((Sc < 80) & (Vc > 220)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=2)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, math.pi / 180, 60, minLineLength=90, maxLineGap=12)
    if lines is None:
        return [((x1 + x2) // 2, (y1 + y2) // 2)]
    segs = sorted([tuple(map(int, l[0])) for l in lines],
                  key=lambda L: math.hypot(L[2] - L[0], L[3] - L[1]), reverse=True)[:6]
    pts = []
    for xa, ya, xb, yb in segs:
        pts.extend(_points_along(xa + x1, ya + y1, xb + x1, yb + y1, spacing))
    out = []
    for px, py in pts:
        if all(abs(px - qx) > 18 or abs(py - qy) > 18 for qx, qy in out):
            out.append((px, py))
    return out[:12]


# ---------- helpers ----------
def _canon(vname: str) -> str:
    v = vname.strip().lower()
    v = v.replace('gobline mines', 'goblin mines').replace('dragon cliff', 'dragon cliffs')
    return {
        'goblin mines': 'Goblin Mines',
        'skeleton park': 'Skeleton Park',
        'golem quarry': 'Golem Quarry',
        'balloon lagoon': 'Balloon Lagoon',
        "builder's workshop": "Builder's Workshop",
        'dragon cliffs': 'Dragon Cliffs',
        'wizard valley': 'Wizard Valley',
        'barbarian camp': 'Barbarian Camp',
        'capital peak': 'Capital Peak',
    }.get(v, vname)


def popup_warning(message: str, title: str = 'Clan Capital') -> bool:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 48 | 4096)
        return True
    except Exception:
        print(f'[POPUP] {title}: {message}')
        return False


def _villages_for_ch_level(ch_level: int) -> list[str]:
    sets = {
        1: {'Capital Peak'},
        2: {'Capital Peak', 'Barbarian Camp'},
        3: {'Capital Peak', 'Barbarian Camp', 'Wizard Valley'},
        4: {'Capital Peak', 'Barbarian Camp', 'Wizard Valley', 'Balloon Lagoon'},
        5: {'Capital Peak', 'Barbarian Camp', 'Wizard Valley',
            'Balloon Lagoon', "Builder's Workshop"},
        6: {'Capital Peak', 'Barbarian Camp', 'Wizard Valley',
            'Balloon Lagoon', "Builder's Workshop", 'Dragon Cliffs'},
        7: {'Capital Peak', 'Barbarian Camp', 'Wizard Valley',
            'Balloon Lagoon', "Builder's Workshop", 'Dragon Cliffs', 'Golem Quarry'},
        8: {'Capital Peak', 'Barbarian Camp', 'Wizard Valley',
            'Balloon Lagoon', "Builder's Workshop", 'Dragon Cliffs',
            'Golem Quarry', 'Skeleton Park'},
        9: {'Goblin Mines', "Builder's Workshop", 'Balloon Lagoon',
            'Capital Peak', 'Dragon Cliffs', 'Barbarian Camp',
            'Skeleton Park', 'Wizard Valley', 'Golem Quarry'},
        10: {'Goblin Mines', "Builder's Workshop", 'Balloon Lagoon',
             'Capital Peak', 'Dragon Cliffs', 'Barbarian Camp',
             'Skeleton Park', 'Wizard Valley', 'Golem Quarry'},
    }
    avail = sets.get(max(1, min(10, ch_level)), sets.get(1))
    return [v for v in CC_VILLAGE_ORDER if v in avail]


def _scan_icons_in_panel(img_bgr, folder_path: str, roi, threshold_pct: int = 80) -> dict:
    results = {}
    if not os.path.isdir(folder_path):
        print(f'[CC P4] ❌ folder missing: {folder_path}')
        return results
    thr = float(threshold_pct) / 100.0
    x1, y1, x2, y2 = roi
    H, W = img_bgr.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(W, x2), min(H, y2)
    if x2 <= x1 or y2 <= y1:
        print('[CC P4] ❌ invalid panel ROI after clamp')
        return results
    panel = img_bgr[y1:y2, x1:x2]
    for name in sorted(os.listdir(folder_path)):
        if not name.lower().endswith('.png'):
            continue
        tpl = imread_unicode(os.path.join(folder_path, name), cv2.IMREAD_COLOR)
        if tpl is None or tpl.size == 0:
            continue
        th, tw = tpl.shape[:2]
        if panel.shape[0] < th or panel.shape[1] < tw:
            continue
        try:
            res = cv2.matchTemplate(panel, tpl, cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(res)
        except cv2.error:
            continue
        print(f'[CC P4] panel match {name}: {score:.2f}')
        if score >= thr:
            results[name] = (x1 + loc[0] + tw // 2, y1 + loc[1] + th // 2, float(score))
    return results


def _load_last_cc_tpl() -> str | None:
    try:
        if os.path.isfile(CLAN_CAPITAL_CACHE):
            with open(CLAN_CAPITAL_CACHE, 'r', encoding='utf-8') as f:
                name = f.read().strip()
            if not name:
                return None
            if os.path.isfile(os.path.join(CLAN_CAPITAL_SCENERY_DIR, name)):
                return name
    except Exception:
        pass
    return None


def _save_last_cc_tpl(name: str) -> None:
    try:
        os.makedirs(os.path.dirname(CLAN_CAPITAL_CACHE), exist_ok=True)
        with open(CLAN_CAPITAL_CACHE, 'w', encoding='utf-8') as f:
            f.write(name)
    except Exception as e:
        print(f'[CLAN CAPITAL] cache save failed: {e}')


def _scan_all_cc_templates(roi_gray, threshold: float):
    best_name, best_score, best_loc, best_shape = None, -1.0, None, None
    for i in range(1, 45):
        name = f'{i}.png'
        tpl_path = os.path.join(CLAN_CAPITAL_SCENERY_DIR, name)
        if not os.path.isfile(tpl_path):
            continue
        tpl = imread_unicode(tpl_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None or tpl.size == 0:
            continue
        th_h, th_w = tpl.shape[:2]
        if roi_gray.shape[0] < th_h or roi_gray.shape[1] < th_w:
            continue
        try:
            res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(res)
        except cv2.error as e:
            print(f'[CLAN CAPITAL] OpenCV error on {name}: {e} → skipping')
            continue
        if score > best_score:
            best_score, best_name, best_loc, best_shape = score, name, loc, (th_h, th_w)
    if best_name and best_score >= threshold:
        return True, best_name, best_score, best_loc, best_shape
    return False, best_name, best_score, best_loc, best_shape


# ---------- main clan capital flow ----------
def clan_capital(cfg, threshold=CLAN_CAPITAL_THRESH, _restart_depth=0) -> bool:
    if not os.path.isdir(CLAN_CAPITAL_SCENERY_DIR):
        print(f'[CLAN CAPITAL] ❌ scenery dir not found: {CLAN_CAPITAL_SCENERY_DIR}')
        return False
    x1s, y1s, x2s, y2s, durs = CC_CAPITAL_SWIPE
    run_adb(['shell', 'input', 'swipe',
             str(x1s), str(y1s), str(x2s), str(y2s), str(durs)])
    pause_event.wait()
    shot_path = take_screenshot('clan_capital.png')
    time.sleep(0.5)
    pause_event.wait()
    img = imread_unicode(shot_path, cv2.IMREAD_GRAYSCALE)
    if img is None or img.size == 0:
        print('[CLAN CAPITAL] ❌ screenshot failed')
        return False
    pause_event.wait()
    x1, y1, x2, y2 = CLAN_CAPITAL_ROI
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        print('[CLAN CAPITAL] ❌ invalid ROI after clamp')
        return False
    roi_gray = img[y1:y2, x1:x2]
    thr = max(0.0, min(1.0, float(threshold)))
    level = int(cfg.get('capital_hall_level', 9))
    pause_event.wait()

    cached = _load_last_cc_tpl()
    if cached:
        tpl_path = os.path.join(CLAN_CAPITAL_SCENERY_DIR, cached)
        tpl = imread_unicode(tpl_path, cv2.IMREAD_GRAYSCALE)
        if (tpl is not None and tpl.size > 0
                and roi_gray.shape[0] >= tpl.shape[0]
                and roi_gray.shape[1] >= tpl.shape[1]):
            try:
                res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
                _, score, _, loc = cv2.minMaxLoc(res)
            except cv2.error as e:
                print(f'[CLAN CAPITAL] OpenCV error on cached {cached}: {e} → will rescan')
                score = -1.0
            if score >= thr:
                th_h, th_w = tpl.shape[:2]
                cx = x1 + loc[0] + th_w // 2
                cy = y1 + loc[1] + th_h // 2
                time.sleep(0.5)
                tap(cx, cy)
                print(f'[CLAN CAPITAL] ✅ tapped (cached) {cached} at ({cx}, {cy})')
                time.sleep(0.5)
                if not clan_capital_phase2():
                    return False
                p3 = clan_capital_phase3(prev_img=None, capital_hall_level=level)
                if p3.get('status') == 'available_found':
                    selected = p3.get('selected')
                    if not selected:
                        return False
                    p4 = clan_capital_phase4(
                        selected_village=selected,
                        is_peak_unlocked=p3.get('peak_unlocked', False),
                    )
                    st = p4.get('status')
                    if st == 'attack_started':
                        return True
                    if st == 'attack_ready_timeout' and _restart_depth < 1:
                        print('[CC] Attack-ready timeout → boot-recover and restart CC flow.')
                        boot_recovery()
                        ensure_home_base()
                        tap(*MENU_TAP)
                        time.sleep(0.6)
                        return clan_capital(cfg, threshold=threshold,
                                            _restart_depth=_restart_depth + 1)
                return False
        else:
            print(f'[CLAN CAPITAL] cached template missing/unusable: {cached} → will rescan')

    ok, name, score, loc, shape = _scan_all_cc_templates(roi_gray, thr)
    if ok:
        th_h, th_w = shape
        cx = x1 + loc[0] + th_w // 2
        cy = y1 + loc[1] + th_h // 2
        time.sleep(0.5)
        tap(cx, cy)
        print(f'[CLAN CAPITAL] ✅ tapped {name} at ({cx}, {cy})')
        _save_last_cc_tpl(name)
        time.sleep(0.5)
        if not clan_capital_phase2():
            return False
        p3 = clan_capital_phase3(prev_img=None, capital_hall_level=level)
        if p3.get('status') == 'available_found':
            selected = p3.get('selected')
            if not selected:
                return False
            p4 = clan_capital_phase4(
                selected_village=selected,
                is_peak_unlocked=p3.get('peak_unlocked', False),
            )
            st = p4.get('status')
            if st == 'attack_started':
                return True
            if st == 'attack_ready_timeout' and _restart_depth < 1:
                print('[CC] Attack-ready timeout → boot-recover and restart CC flow.')
                boot_recovery()
                ensure_home_base()
                tap(*MENU_TAP)
                time.sleep(0.6)
                return clan_capital(cfg, threshold=threshold,
                                    _restart_depth=_restart_depth + 1)
        return False
    print('[CLAN CAPITAL] No template met the threshold; no tap.')
    return False


def clan_capital_phase2(threshold_pct=CC_THRESH_PCT) -> bool:
    shot_path = take_screenshot('clan_capital_phase2.png')
    img = imread_unicode(shot_path, cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        print('[CC] ❌ screenshot failed')
        return False

    trophy_tpl = os.path.join(CLAN_CAPITAL_DIR, 'capital_trophy.png')
    return_tpl = os.path.join(CLAN_CAPITAL_DIR, 'capital_return.png')
    popup_tpl  = os.path.join(CLAN_CAPITAL_DIR, 'capital_popup.png')
    go_tpl     = os.path.join(CLAN_CAPITAL_DIR, 'capital_go.png')
    start_tpl   = os.path.join(CLAN_CAPITAL_DIR, 'capital_game_start.png')
    start_tpl_2 = os.path.join(CLAN_CAPITAL_DIR, 'capital_game_start_2.png')

    ok, score, _ = _match_color(img, trophy_tpl, threshold_pct, roi=CC_V1_ROI)
    print(f'[CC] v1 trophy score={score:.2f} thr={float(threshold_pct)/100:.2f}')
    if not ok:
        ok, score, _ = _match_color(img, return_tpl, threshold_pct, roi=CC_V2_ROI)
        print(f'[CC] v2 return score={score:.2f} thr={float(threshold_pct)/100:.2f}')
        if not ok:
            print('[CC] Not on Clan Capital page → skip.')
            return False

    while True:
        ok, score, pos = _match_color(img, popup_tpl, threshold_pct, roi=None)
        print(f'[CC] popup score={score:.2f} thr={float(threshold_pct)/100:.2f}')
        if not ok:
            break
        tap(*pos)
        time.sleep(0.5)
        shot_path = take_screenshot('cc_after_popup.png')
        img = imread_unicode(shot_path, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            break

    ok, score, pos = _match_color(img, go_tpl, threshold_pct, roi=None)
    print(f'[CC] go score={score:.2f} thr={float(threshold_pct)/100:.2f}')
    if ok and pos:
        tap(*pos)

    ok1, score1, _ = _match_color(img, start_tpl, threshold_pct, roi=CC_START_ROI)
    ok2, score2, _ = _match_color(img, start_tpl_2, threshold_pct, roi=CC_START_ROI)
    print(f'[CC] start#1 score={score1:.2f}  start#2 score={score2:.2f}  thr={float(threshold_pct)/100:.2f}')
    if ok1 or ok2:
        chosen = ('capital_game_start_2.png' if (score2 >= score1 and ok2)
                  else 'capital_game_start.png')
        print(f'[CC] ✅ Clan Capital game started (matched: {chosen}).')
        return True

    tap(*CC_HOME_TAP)
    print('[CC] ❌ Not started → returning home.')
    return False


def clan_capital_phase3(prev_img=None, capital_hall_level: int = 9) -> dict:
    summary = {
        'status': 'ok', 'selected': None, 'selected_coord': None,
        'available': [], 'complete': [], 'busy': [], 'peak_unlocked': False,
    }
    pause_event.wait()

    if prev_img is None:
        shot = take_screenshot('cc_phase3_pre.png')
        pause_event.wait()
        prev_img = imread_unicode(shot, cv2.IMREAD_COLOR)
        if prev_img is None or prev_img.size == 0:
            print('[CC P3] ❌ screenshot failed')
            summary['status'] = 'screenshot_failed'
            return summary

    avail_tpl = os.path.join(CLAN_CAPITAL_DIR, CC_TPL_AVAILABLE_ATKS)
    ok, score, _ = _match_color(prev_img, avail_tpl, 85, roi=CC_AVAIL_ATKS_ROI)
    print(f'[CC P3] available_attacks score={score:.2f} thr=0.85')
    if ok:
        tap(*CC_HOME_TAP)
        print('[CC P3] No attacks available → returning home.')
        summary['status'] = 'no_attacks'
        return summary

    tap(*CC_ENEMY_TAP)
    time.sleep(0.5)
    x1, y1, x2, y2, dur = CC_ENEMY_SWIPE
    run_adb(['shell', 'input', 'swipe',
             str(x1), str(y1), str(x2), str(y2), str(dur)])

    shot = take_screenshot('cc_phase3_enemy.png')
    img = imread_unicode(shot, cv2.IMREAD_COLOR)
    enemy_tpl = os.path.join(CLAN_CAPITAL_DIR, CC_TPL_ENEMY_LAND)
    ok, score, _ = _match_color(img, enemy_tpl, 75, roi=None)
    print(f'[CC P3] enemy_land score={score:.2f} thr=0.75')
    if not ok:
        print('[CC P3] ❌ Enemy page verify failed → rebooting CoC')
        boot_recovery()
        summary['status'] = 'enemy_verify_failed'
        return summary

    unlocked = _villages_for_ch_level(capital_hall_level)
    earlier_all_complete = True

    for v in CC_VILLAGE_ORDER:
        if v not in unlocked:
            continue
        pause_event.wait()

        if v == 'Capital Peak' and not earlier_all_complete:
            print('[CC P3] Capital Peak locked (earlier not 100%). Skipping.')
            summary['peak_unlocked'] = False
            break

        vx, vy = CC_VILLAGE_COORDS[v]
        tap(vx, vy)
        time.sleep(0.5)

        shot = take_screenshot(f"cc_village_{v.replace(' ', '_')}.png")
        vimg = imread_unicode(shot, cv2.IMREAD_COLOR)
        if vimg is None or vimg.size == 0:
            print(f'[CC P3] ❌ screenshot failed on {v} → skipping')
            tap(*CC_CLOSE_PANEL)
            time.sleep(0.5)
            earlier_all_complete = False
            continue

        star_tpl = os.path.join(CLAN_CAPITAL_DIR, CC_TPL_VILLAGE_3STAR)
        ok_star, star_score, _ = _match_color(vimg, star_tpl, 90, roi=CC_VILLAGE_STAR_ROI)
        print(f'[CC P3] {v}: 3star score={star_score:.2f} thr=0.90')
        if ok_star:
            summary['complete'].append(v)
            tap(*CC_CLOSE_PANEL)
            time.sleep(0.5)
            continue

        avail_tpl2 = os.path.join(CLAN_CAPITAL_DIR, CC_TPL_VILLAGE_AVAIL)
        ok_avail, avail_score, _ = _match_color(vimg, avail_tpl2, 92, roi=CC_VILLAGE_AVAIL_ROI)
        print(f'[CC P3] {v}: available score={avail_score:.2f} thr=0.92')
        if ok_avail:
            summary['available'].append(v)
            summary['status'] = 'available_found'
            summary['selected'] = v
            summary['selected_coord'] = (vx, vy)
            summary['peak_unlocked'] = earlier_all_complete
            print(f'[CC P3] ✅ First available target: {v} → stop scanning.')
            return summary

        summary['busy'].append(v)
        tap(*CC_CLOSE_PANEL)
        time.sleep(0.5)
        earlier_all_complete = False

    if 'Capital Peak' in unlocked:
        summary['peak_unlocked'] = earlier_all_complete
    print(f"[CC P3] Summary: available={summary['available']}, "
          f"complete={summary['complete']}, busy={summary['busy']}, "
          f"peak_unlocked={summary['peak_unlocked']}")
    return summary


def clan_capital_phase4(
    selected_village=None,
    threshold_pct=75,
    retry_until_ready=True,
    retry_delay=1.0,
    max_retries=None,
    is_peak_unlocked=False,
) -> dict:
    is_first_attack = False
    vname_canon = _canon(selected_village)
    if vname_canon == 'Capital Peak' and is_peak_unlocked:
        shot_pre = take_screenshot('cc_phase4_precheck.png')
        img_pre = imread_unicode(shot_pre, cv2.IMREAD_COLOR)
        if img_pre is not None and img_pre.size:
            is_first_attack = _is_capital_peak_fresh(img_pre)

    pause_event.wait()
    tap(*CC_ARMY_WINDOW_TAP)
    time.sleep(0.5)
    pause_event.wait()

    tpl_ready = os.path.join(CLAN_CAPITAL_DIR, CC_TPL_TROOPS_READY)
    thr = float(threshold_pct) / 100.0 if threshold_pct > 1 else float(threshold_pct)
    thr = max(0.0, min(1.0, thr))
    pause_event.wait()
    attempts = 0
    while True:
        pause_event.wait()
        shot_path = take_screenshot('cc_phase4_army.png')
        img_ready = imread_unicode(shot_path, cv2.IMREAD_COLOR)
        pause_event.wait()
        if img_ready is None or img_ready.size == 0:
            print('[CC P4] ❌ screenshot failed')
            return {
                'status': 'screenshot_failed',
                'troops_found': [],
                'spells_found': [],
                'drops_done': {'spells': 0, 'troops': 0},
                'attempts': attempts,
            }

        pause_event.wait()
        ok_troops, score_t, _ = _match_color(
            img_ready, tpl_ready, thr, roi=CC_TROOPS_ROI
        )
        print(f'[CC P4] troops score={score_t:.2f} thr={thr:.2f}')
        ok_spells, score_s, _ = _match_color(
            img_ready, tpl_ready, thr, roi=CC_SPELLS_ROI
        )
        print(f'[CC P4] spells score={score_s:.2f} thr={thr:.2f}')

        pause_event.wait()
        if ok_troops and ok_spells:
            break

        pause_event.wait()
        popup_warning(
            'Army not ready: please fix troops or spells before attacking.',
            title='Clan Capital – Army Check',
        )
        attempts += 1
        if not retry_until_ready or (max_retries is not None and attempts >= max_retries):
            return {
                'status': 'not_ready',
                'troops_found': [],
                'spells_found': [],
                'drops_done': {'spells': 0, 'troops': 0},
                'attempts': attempts,
            }
        time.sleep(retry_delay)

    pause_event.wait()
    time.sleep(0.5)
    tap(*CC_ATTACK_TAP)
    time.sleep(0.5)

    pause_event.wait()
    shot_gold = take_screenshot('cc_phase4_goldcheck.png')
    img_gold = imread_unicode(shot_gold, cv2.IMREAD_COLOR)
    pause_event.wait()
    gold_tpl = os.path.join(CLAN_CAPITAL_DIR, CC_TPL_FULL_GOLD_WINDOW)
    ok_gold, gold_score, _ = _match_color(img_gold, gold_tpl, 0.75, roi=CC_FULL_GOLD_ROI)
    print(f'[CC P4] full-gold win score={gold_score:.2f} thr=0.75')
    if ok_gold:
        tap(*CC_REINITIATE_TAP)

    time.sleep(1.0)
    pause_event.wait()

    ar_tpl1 = os.path.join(CLAN_CAPITAL_DIR, 'capital_attack_ready.png')
    ar_tpl2 = os.path.join(CLAN_CAPITAL_DIR, 'capital_attack_ready_2.png')
    thr_f = 0.9
    MAX_READY_POLLS = 14
    attack_ready = False

    for poll in range(1, MAX_READY_POLLS + 1):
        pause_event.wait()
        shot_ar = take_screenshot('cc_phase4_attack_ready.png')
        img_ar = imread_unicode(shot_ar, cv2.IMREAD_GRAYSCALE)
        if img_ar is None or img_ar.size == 0:
            pause_event.wait()
            print(f'[CC P4] ❌ screenshot failed (attack-ready) [try {poll}/{MAX_READY_POLLS}]')
            time.sleep(0.5)
            continue
        pause_event.wait()

        ok1, s1, _ = _match_gray(img_ar, ar_tpl1, thr_f, roi=CC_ATTACK_READY_ROI)
        ok2, s2, _ = _match_gray(img_ar, ar_tpl2, thr_f, roi=CC_ATTACK_READY_ROI)
        pause_event.wait()
        print(f'[CC P4] attack-ready #1 score={s1:.2f}  #2 score={s2:.2f}  '
              f'thr={thr_f:.2f}  [try {poll}/{MAX_READY_POLLS}]')

        if ok1 or ok2:
            pause_event.wait()
            chosen = ('capital_attack_ready_2.png'
                      if (ok2 and s2 >= s1)
                      else 'capital_attack_ready.png')
            print(f'[CC P4] ✅ attack-ready detected using {chosen}')
            time.sleep(0.5)
            attack_ready = True
            break
        time.sleep(0.7)

    if not attack_ready:
        print(f'[CC P4] ❌ attack-ready timeout after {MAX_READY_POLLS} tries → rebooting and restarting CC')
        boot_recovery()
        ensure_home_base()
        tap(*MENU_TAP)
        time.sleep(0.6)
        return {
            'status': 'attack_ready_timeout',
            'troops_found': [],
            'spells_found': [],
            'drops_done': {'spells': 0, 'troops': 0},
            'attempts': attempts,
        }

    pause_event.wait()
    shot_panel = take_screenshot('cc_phase4_panel.png')
    img_panel = imread_unicode(shot_panel, cv2.IMREAD_COLOR)
    if img_panel is None or img_panel.size == 0:
        pause_event.wait()
        print('[CC P4] ❌ screenshot failed (panel)')
        return {
            'status': 'screenshot_failed',
            'troops_found': [],
            'spells_found': [],
            'drops_done': {'spells': 0, 'troops': 0},
            'attempts': attempts,
        }

    spells = _scan_icons_in_panel(img_panel, CC_DIR_SPELLS, CC_PANEL_ROI, threshold_pct=80)
    troops = _scan_icons_in_panel(img_panel, CC_DIR_TROOPS, CC_PANEL_ROI, threshold_pct=80)
    pause_event.wait()
    print(f'[CC P4] spells found: {list(spells.keys())}')
    print(f'[CC P4] troops found: {list(troops.keys())}')

    vname = _canon(selected_village)
    troop_drop = CC_TROOP_DROPPOINTS.get(vname)
    spell_points = CC_SPELL_DROPPOINTS.get(vname, [])

    pause_event.wait()
    drops_troops = 0
    if troops:
        shot_field = take_screenshot('cc_phase4_field.png')
        img_field = imread_unicode(shot_field, cv2.IMREAD_COLOR)

        if img_field is None or img_field.size == 0:
            x1, y1, x2, y2 = _sorted_box(GLOW_TL, GLOW_BR)
            base_drop_points = [((x1 + x2) // 2, (y1 + y2) // 2)]
            stride = 2
            print('[CC P4] Using fallback center point (no field image).')
        else:
            if vname == 'Capital Peak':
                poly_abs = _abs_poly_from_rel(img_field.shape, CP_GLOW_POLY_REL)
                base_drop_points = get_glow_drop_points_poly(
                    img_field, poly_abs, spacing=DROP_SPACING
                )
                if not base_drop_points:
                    base_drop_points = get_glow_drop_points(img_field)
                print(f'[CC P4] Capital Peak (regular-first) points: {len(base_drop_points)} found')
            else:
                base_drop_points = get_glow_drop_points(img_field)

            if not base_drop_points:
                x1, y1, x2, y2 = _sorted_box(GLOW_TL, GLOW_BR)
                base_drop_points = [((x1 + x2) // 2, (y1 + y2) // 2)]
            stride = 2
            print(f"[CC P4] Using {'diamond' if vname == 'Capital Peak' else 'glow'} droppoints (n={len(base_drop_points)}), stride={stride}")

        if (troop_drop and isinstance(troop_drop, tuple)
                and len(troop_drop) == 2):
            sminer_point = troop_drop
        else:
            sminer_point = base_drop_points[0] if base_drop_points else None
            if sminer_point is None:
                x1, y1, x2, y2 = _sorted_box(GLOW_TL, GLOW_BR)
                sminer_point = ((x1 + x2) // 2, (y1 + y2) // 2)

        k = 0
        for fname, (ix, iy, _) in troops.items():
            tap(ix, iy)
            taps = CC_TROOP_TAP_COUNTS.get(fname, 2)

            if fname.lower() == 's_miner.png':
                if vname == 'Capital Peak' and is_first_attack:
                    for t in range(taps):
                        px, py = CP_FIRST_DROPPOINTS[t % len(CP_FIRST_DROPPOINTS)]
                        tap(px, py)
                    drops_troops += taps
                    time.sleep(0.45)
                    continue
                for _ in range(taps):
                    tap(*sminer_point)
                drops_troops += taps
                time.sleep(0.45)
                continue

            for _ in range(taps):
                px, py = base_drop_points[k % len(base_drop_points)]
                tap(px, py)
                k = (k + stride) % len(base_drop_points)
                time.sleep(0.45)
            drops_troops += taps
            time.sleep(0.45)

    pause_event.wait()
    drops_spells = 0
    if spells:
        if spell_points:
            points_seq = list(spell_points)
        else:
            x1, y1, x2, y2 = _sorted_box(GLOW_TL, GLOW_BR)
            points_seq = [((x1 + x2) // 2, (y1 + y2) // 2)]
        random.shuffle(points_seq)

        def _is_jump_or_lightning(name: str) -> bool:
            n = name.lower()
            return 'jump' in n or 'lightning' in n or 'zap' in n

        for i, (fname, (ix, iy, _)) in enumerate(spells.items()):
            taps_needed = 3 if _is_jump_or_lightning(fname) else 1
            if not points_seq:
                x1, y1, x2, y2 = _sorted_box(GLOW_TL, GLOW_BR)
                points_seq = [((x1 + x2) // 2, (y1 + y2) // 2)]
            for j in range(taps_needed):
                tap(ix, iy)
                time.sleep(0.25)
                idx = (i + j * 2) % len(points_seq)
                px, py = points_seq[idx]
                tap(px, py)
                time.sleep(0.35)
                drops_spells += 1
            time.sleep(0.4)

    MAX_VERIFY_ROUNDS = 4
    thr_verify = 85

    orig_spell_names = set(spells.keys())
    orig_troop_names = set(troops.keys())
    cp_mode = 'regular'
    switched_to_fixed = False
    prev_pending = None

    def _safe_playfield_points(pts, img_shape=None):
        if not pts:
            return []
        if img_shape is None:
            y_panel_top = CC_PANEL_ROI[1]
            W = None
        else:
            y_panel_top = CC_PANEL_ROI[1]
            W = img_shape[1]
        y_max = max(0, y_panel_top - 8)
        safe = []
        for x, y in pts:
            if W is not None:
                x = min(W - 20, max(20, x))
            if y >= y_max:
                y = y_max - 1
            safe.append((x, y))
        return safe or pts

    for vr in range(MAX_VERIFY_ROUNDS):
        pause_event.wait()
        shot_v = take_screenshot('cc_phase4_panel_verify.png')
        img_v = imread_unicode(shot_v, cv2.IMREAD_COLOR)
        if img_v is None or img_v.size == 0:
            print('[CC P4] Verify: screenshot failed; stopping verification.')
            break

        spells_left = _scan_icons_in_panel(
            img_v, CC_DIR_SPELLS, CC_PANEL_ROI, threshold_pct=thr_verify
        )
        troops_left = _scan_icons_in_panel(
            img_v, CC_DIR_TROOPS, CC_PANEL_ROI, threshold_pct=thr_verify
        )

        spells_redrop = {
            k: v for k, v in spells_left.items() if k in orig_spell_names
        }
        troops_redrop = {
            k: v for k, v in troops_left.items() if k in orig_troop_names
        }

        if not spells_redrop and not troops_redrop:
            print(f'[CC P4] ✅ Panel clear after {vr} verification round(s).')
            break

        if (vname == 'Capital Peak' and cp_mode == 'regular'
                and (troops_redrop or spells_redrop)
                and not switched_to_fixed):
            cp_mode = 'fixed'
            switched_to_fixed = True
            print('[CC P4] Capital Peak fallback → switching to FIXED CP points for redrops.')

        pending_key = (
            tuple(sorted(spells_redrop.keys())),
            tuple(sorted(troops_redrop.keys())),
            cp_mode,
        )
        if prev_pending == pending_key:
            print('[CC P4] No progress between verification rounds; stopping to avoid loop.')
            break
        prev_pending = pending_key

        print(f'[CC P4] Re-dropping (round {vr + 1}, mode={cp_mode}): '
              f'spells={list(spells_redrop.keys())}, '
              f'troops={list(troops_redrop.keys())}')

        shot_field_v = take_screenshot('cc_phase4_field_verify_src.png')
        img_field_v = imread_unicode(shot_field_v, cv2.IMREAD_COLOR)

        def _regular_points_round():
            if img_field_v is None or img_field_v.size == 0:
                bx1, by1, bx2, by2 = _sorted_box(GLOW_TL, GLOW_BR)
                pts = [((bx1 + bx2) // 2, (by1 + by2) // 2)]
            else:
                if vname == 'Capital Peak':
                    poly_abs = _abs_poly_from_rel(img_field_v.shape, CP_GLOW_POLY_REL)
                    pts = get_glow_drop_points_poly(
                        img_field_v, poly_abs, spacing=DROP_SPACING
                    )
                    if not pts:
                        pts = get_glow_drop_points(img_field_v)
                    print(f'[CC P4] Redrop REGULAR points (Capital Peak, diamond): {len(pts)}')
                else:
                    pts = get_glow_drop_points(img_field_v)
                    print(f'[CC P4] Redrop REGULAR points: {len(pts)}')
            if not pts:
                bx1, by1, bx2, by2 = _sorted_box(GLOW_TL, GLOW_BR)
                pts = [((bx1 + bx2) // 2, (by1 + by2) // 2)]
            return _safe_playfield_points(
                pts,
                img_field_v.shape if img_field_v is not None else None,
            )

        base_regular_points = _regular_points_round()
        base_regular_stride = 2

        if (troop_drop and isinstance(troop_drop, tuple)
                and len(troop_drop) == 2):
            sminer_point = troop_drop
        else:
            sminer_point = (
                base_regular_points[0] if base_regular_points else None
            )
            if sminer_point is None:
                bx1, by1, bx2, by2 = _sorted_box(GLOW_TL, GLOW_BR)
                sminer_point = ((bx1 + bx2) // 2, (by1 + by2) // 2)

        if spells_redrop:
            if spell_points:
                points_seq = _safe_playfield_points(
                    list(spell_points), img_shape=img_v.shape
                )
            else:
                bx1, by1, bx2, by2 = _sorted_box(GLOW_TL, GLOW_BR)
                points_seq = _safe_playfield_points(
                    [((bx1 + bx2) // 2, (by1 + by2) // 2)],
                    img_shape=img_v.shape,
                )
            random.shuffle(points_seq)

            for i, (fname, (ix, iy, _)) in enumerate(spells_redrop.items()):
                taps_needed = 3 if _is_jump_or_lightning(fname) else 1
                if not points_seq:
                    bx1, by1, bx2, by2 = _sorted_box(GLOW_TL, GLOW_BR)
                    points_seq = [((bx1 + bx2) // 2, (by1 + by2) // 2)]
                for j in range(taps_needed):
                    tap(ix, iy)
                    time.sleep(0.25)
                    idx = (i + j * 2) % len(points_seq)
                    px, py = points_seq[idx]
                    tap(px, py)
                    time.sleep(0.35)
                    drops_spells += 1
                time.sleep(0.4)

        k = 0
        if not troops_redrop:
            continue

        for fname, (ix, iy, _) in troops_redrop.items():
            taps = CC_TROOP_TAP_COUNTS.get(fname, 2)
            tap(ix, iy)
            time.sleep(0.15)

            fname_lower = fname.lower()

            if cp_mode == 'fixed' and vname == 'Capital Peak':
                for t in range(taps):
                    px, py = CP_FIRST_DROPPOINTS[t % len(CP_FIRST_DROPPOINTS)]
                    y1p = CC_PANEL_ROI[1]
                    py = min(py, y1p - 1)
                    if fname_lower == 's_miner.png':
                        tap(px, py)
                        drops_troops += 1
                    else:
                        if t == 0:
                            tap(px, py)
                            tap(px, py)
                            drops_troops += 2
                        else:
                            tap(px, py)
                            drops_troops += 1
                    time.sleep(0.4)
                time.sleep(0.45)
                continue

            if fname_lower == 's_miner.png':
                target = (
                    base_regular_points[0] if base_regular_points else sminer_point
                )
                for _ in range(taps):
                    tap(*target)
                    drops_troops += 1
                time.sleep(0.45)
                continue

            for t in range(taps):
                if not base_regular_points:
                    bx1, by1, bx2, by2 = _sorted_box(GLOW_TL, GLOW_BR)
                    px = (bx1 + bx2) // 2
                    py = min((by1 + by2) // 2, CC_PANEL_ROI[1] - 1)
                else:
                    px, py = base_regular_points[k % len(base_regular_points)]
                    k = (k + base_regular_stride) % max(1, len(base_regular_points))
                if t == 0:
                    tap(px, py)
                    tap(px, py)
                    drops_troops += 2
                else:
                    tap(px, py)
                    drops_troops += 1
                time.sleep(0.4)
            time.sleep(0.45)

    return {
        'status': 'attack_started',
        'troops_found': list(troops.keys()),
        'spells_found': list(spells.keys()),
        'drops_done': {'spells': drops_spells, 'troops': drops_troops},
        'attempts': attempts,
    }


def _is_capital_peak_fresh(img_bgr) -> bool:
    ok, score, _ = _match_color(
        img_bgr, CP_FRESH_TEMPLATE, int(CP_FRESH_THRESHOLD * 100), roi=None
    )
    print(f'[CC P4] Capital Peak fresh score={score:.2f} thr={CP_FRESH_THRESHOLD:.2f}')
    return ok
