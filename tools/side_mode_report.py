"""Rebuild the side-mode table + RANDOM distribution from the saved frame.

Reads artifacts/side_mode_frame.png (captured live by test_side_modes.py),
runs the ONNX redline ONCE, then prints each mode's chosen edges and the
RANDOM pick distribution over 2000 planner runs (random.choice only).
"""

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from COCbot.attack.planner import build_attack_plan  # noqa: E402
from COCbot.vision.redline.detector import get_redline_edges_ex  # noqa: E402

MODES = [
    ("Ngẫu nhiên", ["RANDOM"]),
    ("Trên Trái (TL)", ["TL"]),
    ("Trên Phải (TR)", ["TR"]),
    ("Dưới Trái (BL)", ["BL"]),
    ("Dưới Phải (BR)", ["BR"]),
    ("Nửa Trên (TL + TR)", ["TL", "TR"]),
    ("Nửa Dưới (BL + BR)", ["BL", "BR"]),
    ("3 hướng (TR+BR+BL)", ["TR", "BR", "BL"]),
    ("Cả 4 hướng (+)", ["TR", "BR", "BL", "TL"]),
]

img = cv2.imread(str(ROOT / "artifacts" / "side_mode_frame.png"))
if img is None:
    raise SystemExit("artifacts/side_mode_frame.png missing")

edges, source = get_redline_edges_ex(
    img, model_path="", deploy_model_path="models/deploy_zone.onnx"
)
print(f"redline source={source} edges={[len(e) for e in edges]}\n")

print(f"{'mode':24s} {'pick':10s} active edges (points)")
for label, sides in MODES:
    plan = build_attack_plan(edges, {"attack_sides": list(sides), "sides": len(sides)})
    if not plan:
        print(f"{label:24s} PLAN FAILED")
        continue
    counts = [len(e) for e in plan["active_edges"]]
    print(
        f"{label:24s} {plan.get('target_side') or '-':10s} {counts}"
    )

print("\nRANDOM distribution (2000 planner picks, one side each):")
picks = Counter(
    build_attack_plan(edges, {"attack_sides": ["RANDOM"]})["target_side"]
    for _ in range(2000)
)
for side, count in sorted(picks.items()):
    print(f"    {side:4s} {count:4d}/2000  {'#' * (count // 20)}")
