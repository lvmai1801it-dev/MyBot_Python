"""Attack planner: turn raw redline edges into safe, target-aware drop edges.

MyBot logic used here:
- `getRedArea` gives the red line.
- The deployable band is between the red line and the outer (yellow) diamond.
  The OpenCV fallback uses ~35-40% of that band; we use the same ratio.
- `GetAreaForPoint` is replaced by pure Python `side_for_point()` because the
  DLL function is static for 860x732 and the Python version is faster.
"""

import random

from COCbot.vision.redline.geometry import (
    ECD,
    EDGE_BY_SIDE,
    choose_edges,
    ensure_four_edges,
    offset_edges_to_outer,
    side_for_point,
)


def legacy_edge_selection(edges, nb_sides):
    """Preserve the old COCbot.attack.py selection rules when no target is known."""
    if not edges:
        return []
    if nb_sides <= 0:
        nb_sides = 1
    if nb_sides == 2 and len(edges) >= 4:
        return [edges[3], edges[2]]  # TL + BL (old behaviour)
    if nb_sides >= 4:
        return list(edges[:4])
    if nb_sides == 1:
        return [edges[0]]  # TR (old behaviour)
    return list(edges[:3])


def build_attack_plan(edges, cfg=None, target_xy=None):
    """
    Return:
      {
        "edges": offset 4 edges,
        "active_edges": edges to drop on,
        "nb_sides": int,
        "primary_edge": edge for heroes/CC,
        "target_side": "TL"/"TR"/"BL"/"BR"/""
      }
    """
    if not edges:
        return None

    cfg = cfg or {}
    nb_sides = int(cfg.get("sides", 2) or 2)
    ratio = float(cfg.get("redline_offset_ratio", 0.35))

    fixed = offset_edges_to_outer(edges, ECD, ratio=ratio, y_max=615)
    if not ensure_four_edges(fixed):
        # Keep the original edges if the offset filter removed too much.
        fixed = [list(e) for e in edges if e]

    target_side = ""
    attack_sides = cfg.get("attack_sides")
    if attack_sides:
        codes = list(attack_sides)
        if "RANDOM" in codes:
            codes = [random.choice(["TL", "TR", "BL", "BR"])]
        active_edges = []
        for code in codes:
            idx = EDGE_BY_SIDE.get(str(code).upper())
            if idx is not None and idx < len(fixed) and fixed[idx]:
                active_edges.append(fixed[idx])
        target_side = codes[0] if codes else ""
        if active_edges:
            nb_sides = len(active_edges)
    elif target_xy:
        target_side = side_for_point(target_xy[0], target_xy[1])
        if target_side:
            active_edges = choose_edges(fixed, target_side, nb_sides)
            print(
                f"[PLAN] Target {target_xy} -> side {target_side}, "
                f"{len(active_edges)} edge(s)"
            )
        else:
            active_edges = legacy_edge_selection(fixed, nb_sides)
    else:
        active_edges = legacy_edge_selection(fixed, nb_sides)

    if not active_edges:
        active_edges = list(fixed[: max(1, min(4, nb_sides))])

    # Heroes/CC: target edge first; otherwise keep MyBot's TL preference.
    if attack_sides and active_edges or target_xy and target_side and active_edges:
        primary_edge = active_edges[0]
    elif nb_sides >= 3 and len(fixed) >= 4:
        primary_edge = fixed[3]
    elif active_edges:
        primary_edge = active_edges[0]
    else:
        primary_edge = fixed[0] if fixed else None

    return {
        "edges": fixed,
        "active_edges": active_edges,
        "nb_sides": nb_sides,
        "primary_edge": primary_edge,
        "target_side": target_side,
    }
