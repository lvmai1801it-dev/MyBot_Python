"""Deploy-zone ONNX segmentation: the primary redline source.

Port of the external ``deploy_zone_sdk`` (U-Net efficientnet-b4, 3 classes,
IoU ~0.99 vs hand labels). The model file lives at
``models/deploy_zone.onnx`` (gitignored) and predicts, per pixel:

    0 = DEPLOYABLE   troops may be dropped here
    1 = NO_DEPLOY    the red zone around the base (this is the redline)
    2 = INTERFACE    UI to avoid (resource bars, army bar, buttons)

The bot consumes the ``NO_DEPLOY`` boundary exactly like the YOLO
``base_area`` mask: largest contour -> polygon -> ``polygon_to_edges`` ->
[TR, BR, BL, TL] edges, so the planner and dropper stay unchanged.

Only numpy + opencv + onnxruntime are required (no ultralytics/torch).
The 78 MB session is loaded once and cached per resolved path.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from COCbot.vision.redline.geometry import ECD, point_in_poly
from COCbot.vision.redline.yolo import polygon_to_edges, resolve_model_path

Point = Tuple[int, int]

# ImageNet normalization used by the SDK training pipeline.
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)

# The model input is never upscaled; larger frames are shrunk to this edge.
MAX_EDGE = 1280
# The tensor is zero-padded so each side is a multiple of 32.
ALIGN = 32
# Masks smaller than this are treated as "no base on screen".
MIN_MASK_AREA = 500
# Polygon edges are resampled at this spacing before the quadrant split.
RESAMPLE_STEP_PX = 35

CLASS_DEPLOYABLE = 0
CLASS_NO_DEPLOY = 1
CLASS_INTERFACE = 2


class DeployZoneModel:
    """ONNX deploy-zone segmentation with a cached inference session."""

    def __init__(self, model_path: str, device: str = "auto") -> None:
        path = resolve_model_path(model_path)
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"deploy-zone model not found: {model_path}")

        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError(
                "onnxruntime is required for the deploy-zone model. "
                "Install it with: pip install onnxruntime"
            ) from e

        if device == "auto":
            available = ort.get_available_providers()
            device = next(
                (p for p in ("CUDAExecutionProvider", "DmlExecutionProvider")
                 if p in available),
                "cpu",
            )
        provider = {
            "cuda": "CUDAExecutionProvider",
            "dml": "DmlExecutionProvider",
            "cpu": "CPUExecutionProvider",
        }.get(device, device)

        self.model_path = path
        self.sess = ort.InferenceSession(path, providers=[provider])
        self.in_name = self.sess.get_inputs()[0].name
        self.out_name = self.sess.get_outputs()[0].name
        self.providers = self.sess.get_providers()

    def _tensor(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, int, int]:
        """Normalize a BGR frame into a padded NCHW float32 tensor."""
        if img_bgr.ndim == 2 or img_bgr.shape[2] == 1:
            img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]

        k = min(MAX_EDGE / max(w, h), 1.0)
        sw, sh = max(1, round(w * k)), max(1, round(h * k))
        if (sw, sh) != (w, h):
            rgb = cv2.resize(rgb, (sw, sh), interpolation=cv2.INTER_LINEAR)

        x = (rgb.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        tw, th = -(-sw // ALIGN) * ALIGN, -(-sh // ALIGN) * ALIGN
        tensor = np.zeros((1, 3, th, tw), np.float32)
        tensor[0, :, :sh, :sw] = x.transpose(2, 0, 1)
        return tensor, sw, sh

    def predict_cls(self, img_bgr: np.ndarray) -> np.ndarray:
        """Return the uint8 (H, W) class map 0/1/2 at the original size."""
        if img_bgr is None or img_bgr.size == 0:
            return np.zeros((0, 0), np.uint8)

        h, w = img_bgr.shape[:2]
        tensor, sw, sh = self._tensor(img_bgr)
        out = self.sess.run([self.out_name], {self.in_name: tensor})[0][0]
        cls = out.argmax(axis=0)[:sh, :sw].astype(np.uint8)
        if (sw, sh) != (w, h):
            cls = cv2.resize(cls, (w, h), interpolation=cv2.INTER_NEAREST)
        return cls

    def coverage(self, cls: np.ndarray) -> Dict[str, float]:
        """Return the percentage of each class in a predicted map."""
        if cls is None or cls.size == 0:
            return {"deployable": 0.0, "no_deploy": 0.0, "interface": 0.0}
        return {
            name: round(float((cls == idx).mean()) * 100.0, 2)
            for idx, name in enumerate(("deployable", "no_deploy", "interface"))
        }


_MODEL_CACHE: Dict[str, DeployZoneModel] = {}
_MODEL_ERRORS: Dict[str, str] = {}
_LAST_PREDICTION: Optional["DeployZonePrediction"] = None


class DeployZonePrediction:
    """Everything the attack pipeline needs from one ONNX pass."""

    def __init__(self, cls: np.ndarray, polygon: List[Point],
                 edges: List[List[Point]]) -> None:
        self.cls = cls
        self.polygon = polygon
        self.edges = edges
        mask = (cls == CLASS_NO_DEPLOY).astype(np.uint8)
        moments = cv2.moments(mask, binaryImage=True)
        if moments["m00"] > 0:
            self.centroid = (
                moments["m10"] / moments["m00"],
                moments["m01"] / moments["m00"],
            )
        else:
            self.centroid = (cls.shape[1] / 2.0, cls.shape[0] / 2.0)


def get_deploy_zone_model(model_path: str, device: str = "auto") -> Optional[DeployZoneModel]:
    """Load (and cache) the ONNX model; return None when unavailable."""
    resolved = resolve_model_path(model_path)
    if not resolved or not os.path.exists(resolved):
        return None
    if resolved in _MODEL_CACHE:
        return _MODEL_CACHE[resolved]
    if resolved in _MODEL_ERRORS:
        return None
    try:
        model = DeployZoneModel(resolved, device=device)
    except Exception as e:
        _MODEL_ERRORS[resolved] = str(e)
        print(f"[DEPLOY-ZONE] cannot load model: {e}")
        return None
    _MODEL_CACHE[resolved] = model
    return model


def resample_polygon(polygon: Sequence[Point], step_px: int = RESAMPLE_STEP_PX) -> List[Point]:
    """Insert intermediate points so long straight edges carry vertices too.

    ``approxPolyDP`` keeps only the endpoints of a straight segment; a base
    whose whole side is one straight line would otherwise leave a quadrant
    with a single vertex and the [TR, BR, BL, TL] split would fail.
    """
    if not polygon or step_px <= 0:
        return list(polygon or [])
    out: List[Point] = []
    count = len(polygon)
    for i in range(count):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % count]
        out.append((int(x1), int(y1)))
        seg_len = math.hypot(x2 - x1, y2 - y1)
        steps = int(seg_len // step_px)
        for s in range(1, steps + 1):
            t = s / float(steps + 1)
            out.append((
                int(round(x1 + (x2 - x1) * t)),
                int(round(y1 + (y2 - y1) * t)),
            ))
    dedup: List[Point] = []
    for point in out:
        if not dedup or point != dedup[-1]:
            dedup.append(point)
    return dedup


def mask_to_polygon(cls: np.ndarray) -> List[Point]:
    """Return the largest no-deploy contour as a redline polygon.

    Pure numpy/opencv: works on any predicted class map without a model.
    """
    if cls is None or cls.size == 0:
        return []
    mask = (cls == CLASS_NO_DEPLOY).astype(np.uint8) * 255
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < MIN_MASK_AREA:
        return []
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.005 * perimeter, True)
    polygon = [(int(p[0][0]), int(p[0][1])) for p in approx]
    return polygon if len(polygon) >= 4 else []


def redline_edges_from_cls(cls: np.ndarray) -> List[List[Point]]:
    """Convert a predicted class map into [TR, BR, BL, TL] redline edges."""
    polygon = mask_to_polygon(cls)
    if not polygon:
        return []
    return polygon_to_edges(resample_polygon(polygon))


def get_redline_from_deploy_zone(img_bgr: np.ndarray, model_path: str,
                                 device: str = "auto") -> Optional[List[List[Point]]]:
    """Return [TR, BR, BL, TL] edges from the ONNX model, or None.

    The full prediction (class map, polygon, centroid) is kept in
    ``last_prediction()`` so the attack cycle can sanitize its final
    drop points against the same mask without re-running inference.
    """
    global _LAST_PREDICTION
    model = get_deploy_zone_model(model_path, device=device)
    if model is None:
        return None

    try:
        cls = model.predict_cls(img_bgr)
    except Exception as e:
        print(f"[DEPLOY-ZONE] inference failed: {e}")
        return None

    polygon = mask_to_polygon(cls)
    edges = polygon_to_edges(resample_polygon(polygon)) if polygon else []
    _LAST_PREDICTION = DeployZonePrediction(cls, polygon, edges)
    if not edges:
        print("[DEPLOY-ZONE] no usable no-deploy zone in this frame")
        return None

    print(
        f"[DEPLOY-ZONE] redline: coverage={model.coverage(cls)} "
        f"edges={[len(e) for e in edges]}"
    )
    return edges


def last_prediction() -> Optional[DeployZonePrediction]:
    """Return the most recent ONNX prediction for the current frame."""
    return _LAST_PREDICTION


# Nudge an unsafe point outward from the base by these steps before dropping it.
SANITIZE_STEPS_PX = (8, 16, 24, 32, 40)


def _safe_points(points: Sequence[Point], prediction: DeployZonePrediction) -> List[Point]:
    """Keep deployable points; nudge unsafe ones outward; drop the rest.

    A point is safe when the model says ``deployable`` (class 0) and it lies
    inside the deployable map diamond (ECD). Unsafe points are pushed away
    from the base centroid in growing steps; a point that never becomes
    deployable is dropped so the dropper never taps it.
    """
    cls = prediction.cls
    if cls is None or cls.size == 0:
        return list(points or [])
    h, w = cls.shape[:2]
    cx, cy = prediction.centroid

    def inside_map(x: int, y: int) -> bool:
        return point_in_poly(x, y, ECD)

    def deployable(x: int, y: int) -> bool:
        return 0 <= x < w and 0 <= y < h and cls[y, x] == CLASS_DEPLOYABLE

    safe: List[Point] = []
    for point in points or []:
        x, y = int(point[0]), int(point[1])
        if deployable(x, y) and inside_map(x, y):
            safe.append((x, y))
            continue
        dx, dy = x - cx, y - cy
        norm = math.hypot(dx, dy)
        ux, uy = (dx / norm, dy / norm) if norm > 1e-6 else (0.0, -1.0)
        for step in SANITIZE_STEPS_PX:
            nx = int(round(x + ux * step))
            ny = int(round(y + uy * step))
            if deployable(nx, ny) and inside_map(nx, ny):
                safe.append((nx, ny))
                break
    return safe


def sanitize_plan_edges(plan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Validate the planner's offset edges against the last ONNX mask.

    ``build_attack_plan`` offsets redline points outward by a fixed ratio,
    which can push a few of them back into the red zone, into the troop bar,
    or off the map when a base hugs the deployable boundary. This mutates
    each edge list of ``plan["edges"]`` in place, so ``active_edges`` and
    ``primary_edge`` (the same list objects) stay in sync automatically.
    """
    prediction = _LAST_PREDICTION
    if plan is None or prediction is None:
        return plan

    edges = plan.get("edges") or []
    total_before = sum(len(e) for e in edges)
    for edge in edges:
        if isinstance(edge, list):
            edge[:] = _safe_points(edge, prediction)
    total_after = sum(len(e) for e in edges)
    if total_after < total_before:
        print(
            f"[DEPLOY-ZONE] sanitize: {total_before - total_after} unsafe "
            f"drop point(s) nudged or removed"
        )
    return plan


def pick_deploy_points(cls: np.ndarray, n: int = 12, near_px: int = 40,
                       min_gap_px: int = 25) -> List[Point]:
    """Pick n deploy points spread around the base, hugging the red zone.

    Port of the SDK helper: each angular bucket takes the deployable pixel
    closest to the base centre (i.e. nearest the no-deploy boundary), and
    points closer than ``min_gap_px`` to an already-picked one are skipped.
    """
    if cls is None or cls.size == 0 or n <= 0:
        return []
    band = (cls == CLASS_DEPLOYABLE) & cv2.dilate(
        (cls == CLASS_NO_DEPLOY).astype(np.uint8),
        np.ones((near_px, near_px), np.uint8),
    )
    if not band.any():
        band = cls == CLASS_DEPLOYABLE
    ys, xs = np.nonzero(band)
    if len(xs) == 0:
        return []

    cx, cy = float(xs.mean()), float(ys.mean())
    dist = np.hypot(xs - cx, ys - cy)
    bucket = (
        (np.arctan2(ys - cy, xs - cx) + math.pi) / (2 * math.pi) * n
    ).astype(int) % n
    order = np.argsort(dist)

    kept: List[Point] = []
    used_buckets = set()
    for i in order:
        b = int(bucket[i])
        if b in used_buckets:
            continue
        x, y = int(xs[i]), int(ys[i])
        if any((x - px) ** 2 + (y - py) ** 2 < min_gap_px ** 2 for px, py in kept):
            continue
        kept.append((x, y))
        used_buckets.add(b)
        if len(kept) >= n:
            break
    return kept


class DeployZonePolygonSource:
    """Adapter that mimics ``RedlineSegmenter`` for the clean MVVM port.

    Exposes ``predict_polygon(image) -> List[Point]`` and a ``source``
    attribute so ``core.vision.redline.RedlineDetector`` can consume the
    ONNX model without importing this legacy package itself.
    """

    source = "onnx"

    def __init__(self, model_path: str, device: str = "auto") -> None:
        self.model_path = model_path
        self.ok = False
        self.error = ""
        self._model = get_deploy_zone_model(model_path, device=device)
        if self._model is None:
            self.error = f"model not found or unusable: {model_path}"
            return
        self.ok = True

    def predict_polygon(self, img_bgr: np.ndarray) -> List[Point]:
        """Return the no-deploy boundary polygon for an attack frame."""
        if not self.ok or self._model is None or img_bgr is None:
            return []
        try:
            cls = self._model.predict_cls(img_bgr)
        except Exception as e:
            self.error = f"inference failed: {e}"
            return []
        return resample_polygon(mask_to_polygon(cls))


def try_load_polygon_source(model_path: str, device: str = "auto") -> Optional[Any]:
    """Return a polygon source when the ONNX model is usable, else None."""
    if not model_path:
        return None
    source = DeployZonePolygonSource(model_path, device=device)
    if source.ok:
        print(f"[DEPLOY-ZONE] active: {source._model.model_path} "
              f"({', '.join(source._model.providers)})")
        return source
    print(f"[DEPLOY-ZONE] inactive: {source.error}")
    return None
