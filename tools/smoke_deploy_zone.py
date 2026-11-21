"""Smoke: run the deploy-zone ONNX redline over real scout frames.

Verifies the full chain used by the bot: BGR frame -> ONNX cls map ->
polygon -> [TR,BR,BL,TL] edges -> planner offset, plus latency, coverage
and a debug overlay saved to artifacts/.
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from COCbot.attack.planner import build_attack_plan  # noqa: E402
from COCbot.vision.redline.deploy_zone import (  # noqa: E402
    get_deploy_zone_model,
    mask_to_polygon,
    pick_deploy_points,
)
from COCbot.vision.redline.detector import get_redline_edges_ex  # noqa: E402

RAW = ROOT / "datasets" / "redline" / "images" / "raw"
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)

DEPLOY_MODEL = "models/deploy_zone.onnx"

all_images = sorted(RAW.glob("*.jpg"))
step = max(1, len(all_images) // 12)
images = all_images[::step][:12]
model = get_deploy_zone_model(DEPLOY_MODEL)
print(f"provider: {model.providers} | {len(images)} frames")

wins = 0
for path in images:
    img = cv2.imread(str(path))
    if img is None:
        print(f"skip unreadable: {path.name}")
        continue

    t0 = time.perf_counter()
    edges, source = get_redline_edges_ex(
        img, model_path="", deploy_model_path=DEPLOY_MODEL)
    dt = time.perf_counter() - t0

    cls = model.predict_cls(img)
    poly = mask_to_polygon(cls)
    pts = pick_deploy_points(cls, n=12)
    plan = build_attack_plan(edges, {"attack_sides": ["RANDOM"]})
    if source == "onnx":
        wins += 1

    print(f"\n{path.name}")
    print(f"  source={source} edges={[len(e) for e in edges]} {dt:.2f}s")
    print(f"  coverage={model.coverage(cls)} polygon={len(poly)} pts")
    print(f"  deploy_points={len(pts)} "
          f"all_deployable={all(cls[y, x] == 0 for x, y in pts)}")
    if plan:
        print(f"  plan: sides={plan['nb_sides']} "
              f"active={len(plan['active_edges'])} "
              f"target_side={plan['target_side']!r}")

    # Overlay: redline polygon (red), offset active edges (green), points (cyan).
    vis = img.copy()
    if poly:
        cv2.polylines(vis, [np.array(poly, np.int32)], True, (0, 0, 255), 2)
    for edge in (plan or {}).get("active_edges", []):
        for p in edge:
            cv2.circle(vis, (int(p[0]), int(p[1])), 3, (0, 255, 0), -1)
    for x, y in pts:
        cv2.circle(vis, (int(x), int(y)), 5, (255, 255, 0), -1)
    out = OUT / f"deploy_zone_{path.stem}.png"
    cv2.imwrite(str(out), vis)
    print(f"  overlay -> {out.relative_to(ROOT)}")

print(f"\nONNX wins: {wins}/{len(images)} frames")
