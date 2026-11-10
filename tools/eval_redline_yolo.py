"""Evaluate a YOLO-seg redline model on a labeled val set.

Metrics:
- Mask IoU vs ground-truth `base_area` polygons.
- Drop safety: sampled points along predicted edges must be OUTSIDE the GT
  base_area mask (i.e. in the deployable zone).
- Coverage: GT redline points near the predicted polygon.
- Latency: ms per image.

Usage:
  python tools/eval_redline_yolo.py --model models/redline_seg.pt
  python tools/eval_redline_yolo.py --model models/redline_seg.onnx --limit 100
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from COCbot.vision.redline.yolo import (  # noqa: E402
    RedlineSegmenter,
    polygon_to_edges,
)


def load_gt_mask(label_path, w, h):
    mask = np.zeros((h, w), dtype=np.uint8)
    if not os.path.exists(label_path):
        return mask
    with open(label_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            try:
                coords = list(map(float, parts[1:]))
            except ValueError:
                continue
            pts = []
            for i in range(0, len(coords) - 1, 2):
                pts.append([int(coords[i] * w), int(coords[i + 1] * h)])
            if len(pts) >= 3:
                cv2.fillPoly(mask, [np.array(pts, dtype=np.int32)], 255)
    return mask


def mask_iou(a, b):
    inter = int(np.count_nonzero((a > 0) & (b > 0)))
    union = int(np.count_nonzero((a > 0) | (b > 0)))
    return inter / union if union else 0.0


def sample_polyline(points, step=12):
    out = []
    if not points:
        return out
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dist = max(1, int(np.hypot(x2 - x1, y2 - y1)))
        for d in range(0, dist, step):
            t = d / dist
            out.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)))
    if points:
        out.append(points[-1])
    return out


def evaluate(model_path, data_dir, imgsz, conf, limit):
    img_dir = os.path.join(data_dir, "images", "val")
    lbl_dir = os.path.join(data_dir, "labels", "val")
    images = sorted(n for n in os.listdir(img_dir)
                    if n.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
    if limit > 0:
        images = images[:limit]

    if not images:
        print("No val images in", img_dir)
        return

    seg = RedlineSegmenter(model_path, imgsz=imgsz, conf=conf)
    if not seg.ok:
        print("Cannot load model:", seg.error)
        return

    total_iou = 0.0
    total_safe = 0
    total_points = 0
    total_covered = 0
    total_gt_points = 0
    total_ms = 0.0
    used = 0

    for name in images:
        img_path = os.path.join(img_dir, name)
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        gt = load_gt_mask(os.path.join(lbl_dir, os.path.splitext(name)[0] + ".txt"), w, h)
        if not np.any(gt):
            continue

        t0 = time.perf_counter()
        poly = seg.predict_polygon(img)
        total_ms += (time.perf_counter() - t0) * 1000
        used += 1

        # Predicted mask for IoU.
        pred = np.zeros((h, w), dtype=np.uint8)
        if poly:
            cv2.fillPoly(pred, [np.array(poly, dtype=np.int32)], 255)
        total_iou += mask_iou(pred, gt)

        edges = polygon_to_edges(poly) if poly else []
        if edges:
            for edge in edges:
                for x, y in sample_polyline(edge):
                    total_points += 1
                    if 0 <= x < w and 0 <= y < h and gt[y, x] == 0:
                        total_safe += 1

        # Coverage: how many GT boundary points are near the predicted polygon.
        gt_contours, _ = cv2.findContours(gt, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if gt_contours and poly:
            gt_contour = max(gt_contours, key=cv2.contourArea)
            pred_contour = np.array(poly, dtype=np.int32)
            for p in gt_contour[::max(1, len(gt_contour) // 100)]:
                total_gt_points += 1
                d = cv2.pointPolygonTest(pred_contour, (int(p[0][0]), int(p[0][1])), True)
                if abs(d) <= 10:
                    total_covered += 1

    if used == 0:
        print("No usable images.")
        return

    print("=" * 50)
    print(f"images       : {used}")
    print(f"mask IoU     : {total_iou / used:.4f}")
    print(f"drop safety  : {total_safe / max(1, total_points):.4f} "
          f"({total_safe}/{total_points})")
    print(f"coverage     : {total_covered / max(1, total_gt_points):.4f} "
          f"({total_covered}/{total_gt_points})")
    print(f"latency      : {total_ms / used:.1f} ms/image")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Evaluate redline YOLO-seg")
    parser.add_argument("--model", default=os.path.join(ROOT, "models", "redline_seg.pt"))
    parser.add_argument("--data", default=os.path.join(ROOT, "datasets", "redline"))
    parser.add_argument("--imgsz", type=int, default=736)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    evaluate(args.model, args.data, args.imgsz, args.conf, args.limit)


if __name__ == "__main__":
    main()
