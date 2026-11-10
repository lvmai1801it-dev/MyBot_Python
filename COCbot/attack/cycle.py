"""Attack cycle orchestration.

This is the Python equivalent of MyBot's AttackCycle + AttackMain:
  capture -> redline -> plan (side/offset) -> prepare army -> drop -> verify.
"""

import time

from COCbot.attack.device import (
    check_slot_has_troops,
    select_drop_troop,
    set_sleep,
)
from COCbot.attack.dropper import (
    drop_cc,
    drop_heroes_v2,
    drop_on_active_edges,
    drop_spells,
)
from COCbot.attack.planner import build_attack_plan
from COCbot.vision.redline.detector import get_redline_edges_ex
from COCbot.attack.army import prepare_attack
from COCbot.vision.capture import take_screenshot
from COCbot.vision.redline.dataset_capture import get_capture


def _capture_attack_image():
    """Capture a non-cloudy frame; return None on failure."""
    img = None
    for _ in range(5):
        img = take_screenshot()
        if img is None:
            time.sleep(0.5)
            continue
        if img.mean() > 220:
            print("[ATTACK] Dang trong hieu ung may trang, cho 1s...")
            time.sleep(1.0)
            continue
        return img
    return img


def _sort_troops(atk_troops):
    tanks = ['golem', 'ice_golem', 'giant', 'pekka', 'root_rider',
             'barbarian', 'valkyrie']
    main_attack = ['dragon', 'electro_dragon', 'baby_dragon', 'dragon_rider',
                   'balloon', 'wizard', 'witch', 'bowler', 'miner',
                   'hog_rider', 'archer', 'minion']

    def priority(troop):
        lname = troop.get('name', '').lower()
        for idx, t in enumerate(tanks):
            if t in lname:
                return (0, idx)
        for idx, m in enumerate(main_attack):
            if m in lname:
                return (1, idx)
        return (2, 0)

    return sorted(atk_troops.values(), key=priority)


def run_attack(cfg):
    print("[ATTACK] === BAT DAU TRAN DANH ===")

    img = _capture_attack_image()
    if img is None:
        print("[ERROR] Khong chup duoc man hinh!")
        return

    model_path = (cfg or {}).get('redline_model', '')
    edges, redline_source = get_redline_edges_ex(img, model_path=model_path)

    # Active learning: save hard (fallback) frames automatically while attacking.
    try:
        get_capture(cfg).maybe_capture(
            img,
            tag=f"attack_{redline_source}",
            source=redline_source,
            meta={
                "sides": (cfg or {}).get('sides', 2),
                "target_xy": (cfg or {}).get('target_xy'),
                "edge_counts": [len(e) for e in edges] if edges else None,
                "redline_model": model_path,
            },
        )
    except Exception as e:
        print(f"[CAPTURE] skipped: {e}")

    if not edges:
        print("[ERROR] Khong tim thay Redline, huy danh!")
        return

    plan = build_attack_plan(
        edges,
        cfg,
        target_xy=(cfg or {}).get('target_xy'),
    )
    if not plan:
        print("[ERROR] Khong tao duoc attack plan!")
        return

    active_edges = plan['active_edges']
    print(f"[PLAN] sides={plan['nb_sides']} "
          f"active_edges={len(active_edges)} "
          f"target_side={plan.get('target_side', '') or '-'}")

    atk_troops, heroes_slots, cc_slot = prepare_attack(img)

    has_troops = bool(atk_troops)
    has_heroes = bool(heroes_slots and any(v >= 0 for v in heroes_slots.values()))
    if not has_troops and not has_heroes:
        print("[ERROR] Khong co quan hoac hero nao tren thanh! Huy danh.")
        return

    sorted_troops = _sort_troops(atk_troops)

    for info in sorted_troops:
        if info.get('is_spell', False):
            continue

        troop_name = info.get('name', '?')
        current_count = int(info.get('count', 0) or 0)
        if current_count <= 0:
            continue

        lname = troop_name.lower()
        if any(t in lname for t in ['giant', 'golem', 'pekka']):
            slots = 4 if current_count <= 10 else 6
        elif any(a in lname for a in ['dragon', 'electro_dragon', 'balloon']):
            slots = 6
        else:
            slots = 8

        for attempt in range(3):
            print(f"[ATTACK] Tha {current_count} {troop_name} "
                  f"(Slot {info['slot']}, lan {attempt + 1})...")
            select_drop_troop(info['slot'])
            time.sleep(0.15)

            drop_on_active_edges(active_edges, current_count, slots_per_edge=slots)
            time.sleep(0.3)

            verify_img = take_screenshot()
            if verify_img is None:
                break

            has_left, rem_count = check_slot_has_troops(verify_img, info['slot'])
            if not has_left or rem_count <= 0:
                print(f"[ATTACK] Slot {info['slot']} ({troop_name}) da het quan.")
                break
            print(f"[ATTACK] Slot {info['slot']} ({troop_name}) "
                  f"van con ~{rem_count} quan! Tha tiep...")
            current_count = rem_count

        time.sleep(set_sleep(0))

    if has_heroes:
        drop_heroes_v2(img, plan['edges'], heroes_slots,
                       primary_edge=plan['primary_edge'])

    if cc_slot is not None and cc_slot >= 0:
        drop_cc(cc_slot, plan['primary_edge'])

    drop_spells(sorted_troops, active_edges, plan['edges'])

    # Final sweep: catch any troop slot that still has a badge.
    final_img = take_screenshot()
    if final_img is not None:
        for slot_idx in range(11):
            has_left, rem = check_slot_has_troops(final_img, slot_idx)
            if has_left and rem > 0:
                print(f"[ATTACK] Phat hien Slot {slot_idx} con sot ~{rem} quan, tha not...")
                select_drop_troop(slot_idx)
                time.sleep(0.15)
                drop_on_active_edges(active_edges, rem, slots_per_edge=2)
                time.sleep(0.2)

    print("[ATTACK] === DA THA XONG ===")
