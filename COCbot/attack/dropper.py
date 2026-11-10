"""Troop/hero/spell dropping primitives.

Keeps the existing fast multi-point behaviour and adds an API that accepts a
dynamic list of active edges (used by planner.py).
"""

import time
import random

from COCbot.attack.device import tap, select_drop_troop
from COCbot.vision.redline.geometry import edge_midpoint


def get_spread_points_along_edge(edge, num_points=8):
    """Spread num_points along an edge (real redline points or a straight line)."""
    if not edge:
        return []
    if len(edge) == 1:
        return [edge[0]]

    if len(edge) >= num_points:
        start_idx = max(0, int(len(edge) * 0.05))
        end_idx = min(len(edge) - 1, int(len(edge) * 0.95))
        if end_idx <= start_idx:
            start_idx = 0
            end_idx = len(edge) - 1

        sub_edge = edge[start_idx:end_idx + 1]
        if len(sub_edge) <= 1:
            return [edge[0]]

        step = (len(sub_edge) - 1) / max(1, (num_points - 1))
        return [sub_edge[int(round(i * step))] for i in range(num_points)]

    p_start = edge[0]
    p_end = edge[-1]
    sx = p_start[0] + (p_end[0] - p_start[0]) * 0.05
    sy = p_start[1] + (p_end[1] - p_start[1]) * 0.05
    ex = p_start[0] + (p_end[0] - p_start[0]) * 0.95
    ey = p_start[1] + (p_end[1] - p_start[1]) * 0.95

    if num_points <= 1:
        return [(int((sx + ex) / 2), int((sy + ey) / 2))]

    pts = []
    for i in range(num_points):
        ratio = i / (num_points - 1)
        pts.append((int(sx + (ex - sx) * ratio), int(sy + (ey - sy) * ratio)))
    return pts


def drop_multipoint_concurrent(points_list, number, delay=0.005):
    """Drop troops concurrently across all points in short waves."""
    if number <= 0 or not points_list:
        return

    dropped = 0
    while dropped < number:
        for pt in points_list:
            if dropped >= number:
                break
            off_x = random.randint(-3, 3)
            off_y = random.randint(-3, 3)
            tap(pt[0] + off_x, pt[1] + off_y, delay=delay)
            dropped += 1

        if dropped < number:
            time.sleep(random.uniform(0.01, 0.025))


def drop_on_edge(edge, number, slots_per_edge=0, edge2=None):
    """Drop along one edge, or interleave two edges."""
    if number <= 0 or not edge:
        return

    if slots_per_edge > 0:
        num_pts = slots_per_edge
    else:
        num_pts = max(6, min(12, number))

    pts1 = get_spread_points_along_edge(edge, num_pts)
    pts2 = get_spread_points_along_edge(edge2, num_pts) if edge2 else None

    combined_pts = []
    max_len = max(len(pts1), len(pts2) if pts2 else 0)
    for i in range(max_len):
        if i < len(pts1):
            combined_pts.append(pts1[i])
        if pts2 and i < len(pts2):
            combined_pts.append(pts2[i])

    drop_multipoint_concurrent(combined_pts, number)


def drop_on_active_edges(active_edges, number, slots_per_edge=0):
    """Drop on an arbitrary list of edges (1..4).

    This is the new entry point used by cycle.py. It replaces the hardcoded
    edges[3]/edges[2]/edges[0] logic in the old drop_on_edges().
    """
    if number <= 0 or not active_edges:
        return

    num_pts = slots_per_edge if slots_per_edge > 0 else max(6, min(10, number))
    active_edges = [e for e in active_edges if e]

    if len(active_edges) == 1:
        drop_on_edge(active_edges[0], number, slots_per_edge=num_pts)
        return

    if len(active_edges) == 2:
        drop_on_edge(active_edges[0], number,
                     slots_per_edge=num_pts, edge2=active_edges[1])
        return

    all_pts_per_edge = [get_spread_points_along_edge(e, num_pts)
                        for e in active_edges[:4]]
    combined_pts = []
    for p_idx in range(num_pts):
        for edge_pts in all_pts_per_edge:
            if p_idx < len(edge_pts):
                combined_pts.append(edge_pts[p_idx])
    drop_multipoint_concurrent(combined_pts, number)


def drop_on_edges(edges, nb_sides, number, slots_per_edge=0):
    """Backward-compatible wrapper around the old side-selection rules."""
    if number <= 0 or not edges:
        return

    if nb_sides <= 0:
        nb_sides = 1

    if nb_sides == 2 and len(edges) >= 4:
        active = [edges[3], edges[2]]
    elif nb_sides >= 4:
        active = list(edges[:4])
    elif nb_sides == 1:
        active = [edges[0]]
    else:
        active = list(edges[:3])

    drop_on_active_edges(active, number, slots_per_edge)


def drop_heroes_v2(_img, edges, hero_slots, primary_edge=None):
    if not hero_slots:
        return False

    print("[ATTACK] Bat dau tha Heroes...")
    if primary_edge:
        drop_point = edge_midpoint(primary_edge)
    elif edges and len(edges) > 3 and edges[3]:
        drop_point = edge_midpoint(edges[3])
    elif edges:
        drop_point = edge_midpoint(edges[0])
    else:
        drop_point = (150, 400)

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


def drop_cc(cc_slot, primary_edge=None):
    """Drop Clan Castle / Siege at the middle of the primary edge."""
    if cc_slot is None or cc_slot < 0:
        return False
    print(f"[ATTACK] Tha Clan Castle / Siege (Slot {cc_slot})...")
    select_drop_troop(cc_slot)
    time.sleep(0.2)
    pt = edge_midpoint(primary_edge) if primary_edge else (430, 350)
    tap(pt[0], pt[1])
    time.sleep(0.3)
    return True


def drop_spells(spell_infos, active_edges, all_edges):
    """Drop spells near the middle of the active front."""
    p1 = edge_midpoint(active_edges[0]) if active_edges else (500, 300)
    if len(active_edges) > 1:
        p2 = edge_midpoint(active_edges[1])
    elif all_edges and len(all_edges) > 2:
        p2 = edge_midpoint(all_edges[2])
    else:
        p2 = (300, 500)

    mid_x = (p1[0] + p2[0]) // 2
    mid_y = (p1[1] + p2[1]) // 2

    for info in spell_infos:
        if not info.get('is_spell', False):
            continue
        count = int(info.get('count', 0) or 0)
        if count <= 0:
            continue
        print(f"[ATTACK] Tha Spell {info.get('name', '?')} (x{count})...")
        select_drop_troop(info['slot'])
        time.sleep(0.2)
        for _ in range(count):
            tap(mid_x + random.randint(-30, 30),
                mid_y + random.randint(-30, 30))
            time.sleep(0.3)
