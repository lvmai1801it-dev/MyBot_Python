"""
redline_geometry.py - Pure-Python geometry helpers for the redline.

The 860x732 canvas constants and quadrant rules are embedded here as pure
Python functions. They replace the old external-DLL helpers and avoid a 32-bit
subprocess call per point.

Reference values on a 860x732 screenshot:
  DCD -> 420,65 | 800,345 | 425,630 | 40,350
  ECD -> 425,15 | 860,345 | 425,675 | 0,355 | 0,335
  FV  -> 0,0 | 860,0 | 860,780 | 0,780

  side_for_point(430,366) -> BR
  side_for_point(300,300) -> TL
  side_for_point(500,300) -> TR
  side_for_point(300,450) -> BL
  side_for_point(100,200) -> ""   (outside ECD)
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

Point = Tuple[int, int]

# Game canvas (860x732).
SCREEN_W = 860
SCREEN_H = 732

# Quadrant center used by side_for_point().
CENTER: Point = (425, 345)

# UI / troop bar starts around y=615; never tap below this.
UI_BOTTOM = 615

# getDiamondString("DCD") - inner diamond.
DCD: List[Point] = [
    (420, 65),
    (800, 345),
    (425, 630),
    (40, 350),
]

# getDiamondString("ECD") - outer deployable diamond.
# The DLL returns 5 points; the last two are both on the left edge.
ECD: List[Point] = [
    (425, 15),
    (860, 345),
    (425, 675),
    (0, 355),
    (0, 335),
]


def parse_points(text: str, sep: str = "|", coord_sep: str = ",") -> List[Point]:
    """Parse 'x,y|x,y' or 'x-y|x-y' into a list of int points."""
    out: List[Point] = []
    if not text:
        return out
    for token in text.replace("-", coord_sep).split(sep):
        parts = token.strip().split(coord_sep)
        if len(parts) != 2:
            continue
        try:
            out.append((int(float(parts[0])), int(float(parts[1]))))
        except (ValueError, TypeError):
            continue
    return out


def point_in_poly(x: float, y: float, poly: Sequence[Point]) -> bool:
    """Ray-casting point-in-polygon test."""
    if len(poly) < 3:
        return False
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def clamp_point(p: Point, y_max: int = UI_BOTTOM) -> Point:
    """Clamp a point into the safe screen area (above the troop bar)."""
    x = max(10, min(SCREEN_W - 10, int(p[0])))
    y = max(35, min(y_max, int(p[1])))
    return (x, y)


def nearest_on_segment(p: Point, a: Point, b: Point) -> Point:
    """Closest point on segment a-b to p."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return a
    t = ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return (int(round(ax + t * dx)), int(round(ay + t * dy)))


def nearest_on_polygon(p: Point, poly: Sequence[Point]) -> Point:
    """Closest point on the boundary of a polygon."""
    if len(poly) < 2:
        return p
    best = poly[0]
    best_d = float("inf")
    for i in range(len(poly)):
        q = nearest_on_segment(p, poly[i], poly[(i + 1) % len(poly)])
        d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
        if d < best_d:
            best_d = d
            best = q
    return best


def filter_edge(
    edge: Sequence[Point],
    outer: Sequence[Point] = ECD,
    y_max: int = UI_BOTTOM,
) -> List[Point]:
    """Keep only points inside the outer diamond and above the UI bar."""
    if not edge:
        return []
    result = []
    for p in edge:
        x, y = p
        if y > y_max:
            continue
        if outer and not point_in_poly(x, y, outer):
            continue
        result.append(clamp_point((x, y), y_max))
    return result


def offset_edge_to_outer(
    edge: Sequence[Point],
    outer: Sequence[Point] = ECD,
    ratio: float = 0.35,
    y_max: int = UI_BOTTOM,
) -> List[Point]:
    """
    Move a redline edge outward toward the outer (yellow) diamond.

    ratio=0.0 keeps the redline; ratio=1.0 lands on the outer diamond.
    MyBot's OpenCV fallback uses roughly 35-40% of the band, so 0.35 is a good
    starting point.
    """
    if not edge:
        return []
    if not outer:
        return [clamp_point(p, y_max) for p in edge]

    result: List[Point] = []
    for p in edge:
        target = nearest_on_polygon(p, outer)
        x = p[0] + (target[0] - p[0]) * ratio
        y = p[1] + (target[1] - p[1]) * ratio
        result.append(clamp_point((int(round(x)), int(round(y))), y_max))
    return result


def offset_edges_to_outer(
    edges: Sequence[Sequence[Point]],
    outer: Sequence[Point] = ECD,
    ratio: float = 0.35,
    y_max: int = UI_BOTTOM,
) -> List[List[Point]]:
    """Apply offset_edge_to_outer to all 4 edges (TR, BR, BL, TL order)."""
    out: List[List[Point]] = []
    for edge in edges:
        fixed = offset_edge_to_outer(edge, outer, ratio, y_max)
        if len(fixed) >= 3:
            out.append(fixed)
    return out


def side_for_point(x: float, y: float, outer: Sequence[Point] = ECD) -> str:
    """
    Pure-Python replacement for the old external-DLL point classifier.

    Returns "TL" / "TR" / "BL" / "BR", or "" when the point is outside ECD.
    """
    if outer and not point_in_poly(x, y, outer):
        return ""
    cx, cy = CENTER
    if x < cx and y < cy:
        return "TL"
    if x >= cx and y < cy:
        return "TR"
    if x < cx and y >= cy:
        return "BL"
    return "BR"


# Edge order used by COCbot.attack.py: [TR, BR, BL, TL]
EDGE_BY_SIDE = {"TR": 0, "BR": 1, "BL": 2, "TL": 3}


def choose_edges(
    edges: Sequence[Sequence[Point]],
    target_side: str,
    nb_sides: int = 2,
) -> List[Sequence[Point]]:
    """
    Return the active edges to attack, starting from the side nearest the
    target and expanding to adjacent sides.

    edges must be in [TR, BR, BL, TL] order.
    """
    if not edges:
        return []
    nb_sides = max(1, min(4, int(nb_sides)))
    idx = EDGE_BY_SIDE.get(target_side.upper(), 0)
    order = [idx, (idx + 1) % 4, (idx - 1) % 4, (idx + 2) % 4]
    picked = [edges[i] for i in order[:nb_sides] if i < len(edges) and edges[i]]
    return picked


def edge_midpoint(edge: Sequence[Point]) -> Point:
    if not edge:
        return CENTER
    return edge[len(edge) // 2]


def ensure_four_edges(edges: Sequence[Sequence[Point]]) -> bool:
    """True when all 4 sides have at least 3 usable points."""
    return len(edges) == 4 and all(len(e) >= 3 for e in edges)
