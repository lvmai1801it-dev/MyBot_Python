"""Redline (no-deploy zone) detection: YOLO-seg first, OpenCV fallback."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np

from COCbot.core.config import defaults
from COCbot.core.config.paths import get_project_paths
from COCbot.core.ports import LoggerPort
from COCbot.core.vision.image import frame_image
from COCbot.models.attack import RedlineResult
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point

PointTuple = tuple[int, int]

CENTER: PointTuple = (425, 345)
UI_BOTTOM = 615
ECD: tuple[PointTuple, ...] = (
    (425, 15),
    (860, 345),
    (425, 675),
    (0, 355),
    (0, 335),
)


def _point_in_poly(x: float, y: float, poly: Sequence[PointTuple]) -> bool:
    """Return ``True`` when ``(x, y)`` is inside *poly*."""
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


def _clamp_point(point: PointTuple, y_max: int = UI_BOTTOM) -> PointTuple:
    """Clamp a point above the troop bar and inside the screen."""
    x = max(10, min(defaults.SCREEN_WIDTH - 10, int(point[0])))
    y = max(35, min(y_max, int(point[1])))
    return (x, y)


def _nearest_on_segment(point: PointTuple, a: PointTuple, b: PointTuple) -> PointTuple:
    """Return the closest point on segment ``a-b`` to *point*."""
    ax, ay = a
    bx, by = b
    px, py = point
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return a
    t = ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return (int(round(ax + t * dx)), int(round(ay + t * dy)))


def _nearest_on_polygon(point: PointTuple, poly: Sequence[PointTuple]) -> PointTuple:
    """Return the closest point on the boundary of *poly*."""
    if len(poly) < 2:
        return point
    best = poly[0]
    best_distance = float("inf")
    for index in range(len(poly)):
        candidate = _nearest_on_segment(
            point, poly[index], poly[(index + 1) % len(poly)]
        )
        distance = (candidate[0] - point[0]) ** 2 + (candidate[1] - point[1]) ** 2
        if distance < best_distance:
            best_distance = distance
            best = candidate
    return best


def side_for_point(x: float, y: float, outer: Sequence[PointTuple] = ECD) -> str:
    """Classify a point as ``TL``/``TR``/``BL``/``BR`` (empty outside)."""
    if outer and not _point_in_poly(x, y, outer):
        return ""
    cx, cy = CENTER
    if x < cx and y < cy:
        return "TL"
    if x >= cx and y < cy:
        return "TR"
    if x < cx and y >= cy:
        return "BL"
    return "BR"


def polygon_to_edges(poly: Sequence[PointTuple]) -> list[list[PointTuple]]:
    """Split a closed redline polygon into ``[TR, BR, BL, TL]`` edges."""
    if not poly or len(poly) < 4:
        return []
    sides: dict[str, list[PointTuple]] = {"TR": [], "BR": [], "BL": [], "TL": []}
    for x, y in poly:
        side = side_for_point(x, y)
        if side:
            sides[side].append((int(x), int(y)))
    for side, points in sides.items():
        if side in ("TL", "TR"):
            points.sort(key=lambda item: (item[0], item[1]))
        else:
            points.sort(key=lambda item: (item[0], -item[1]))
    if any(len(sides[side]) < 2 for side in ("TR", "BR", "BL", "TL")):
        return []
    return [sides["TR"], sides["BR"], sides["BL"], sides["TL"]]


def offset_edges_to_outer(
    edges: Sequence[Sequence[PointTuple]],
    outer: Sequence[PointTuple] = ECD,
    ratio: float = defaults.DEFAULT_REDLINE_OFFSET_RATIO,
    y_max: int = UI_BOTTOM,
) -> list[list[PointTuple]]:
    """Move each edge outward toward the yellow deploy boundary."""
    result: list[list[PointTuple]] = []
    for edge in edges:
        moved: list[PointTuple] = []
        for point in edge:
            target = _nearest_on_polygon(point, outer)
            x = point[0] + (target[0] - point[0]) * ratio
            y = point[1] + (target[1] - point[1]) * ratio
            moved.append(_clamp_point((int(round(x)), int(round(y))), y_max))
        if len(moved) >= 3:
            result.append(moved)
    return result


def _redline_cv_geometry(
    image: np.ndarray,
    tolerance: int = 25,
    inset: int = 0,
) -> tuple[list[list[PointTuple]], list[PointTuple]]:
    """Pure OpenCV isometric fallback: inset edges + redline polygon."""
    height, width = image.shape[:2]
    center_x, center_y = CENTER
    blue = image[:, :, 0].astype(int)
    green = image[:, :, 1].astype(int)
    red = image[:, :, 2].astype(int)

    village = np.zeros((height, width), dtype=bool)
    village[40:650, 20:840] = True
    red_match = (
        (red > green + 20)
        & (red > blue + 35)
        & (red > 90)
        & village
    )
    ys, xs = np.where(red_match)
    if len(xs) > 20:
        dx = int(np.percentile(np.abs(xs - center_x), 95))
        dy = int(np.percentile(np.abs(ys - center_y), 95))
        dx = max(400, min(415, dx))
        dy = max(315, min(335, dy))
    else:
        dx, dy = 410, 325

    top = (center_x, center_y - dy)
    bottom = (center_x, center_y + dy)
    left = (center_x - dx, center_y)
    right = (center_x + dx, center_y)

    def parallel_offset(p1: PointTuple, p2: PointTuple, distance: int = 40) -> list[PointTuple]:
        delta_x = p2[0] - p1[0]
        delta_y = p2[1] - p1[1]
        length = math.hypot(delta_x, delta_y)
        if length == 0:
            return [p1] * 5
        normal_a = (-delta_y / length, delta_x / length)
        normal_b = (delta_y / length, -delta_x / length)
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        outward = (mid[0] - center_x, mid[1] - center_y)
        normal = (
            normal_a
            if normal_a[0] * outward[0] + normal_a[1] * outward[1]
            > normal_b[0] * outward[0] + normal_b[1] * outward[1]
            else normal_b
        )
        first = (
            max(10, min(width - 10, int(p1[0] + normal[0] * distance))),
            max(35, min(UI_BOTTOM, int(p1[1] + normal[1] * distance))),
        )
        second = (
            max(10, min(width - 10, int(p2[0] + normal[0] * distance))),
            max(35, min(UI_BOTTOM, int(p2[1] + normal[1] * distance))),
        )
        return [
            first,
            (
                int(first[0] + (second[0] - first[0]) * 0.25),
                int(first[1] + (second[1] - first[1]) * 0.25),
            ),
            (
                int(first[0] + (second[0] - first[0]) * 0.5),
                int(first[1] + (second[1] - first[1]) * 0.5),
            ),
            (
                int(first[0] + (second[0] - first[0]) * 0.75),
                int(first[1] + (second[1] - first[1]) * 0.75),
            ),
            second,
        ]

    edges = [
        parallel_offset(top, right, -inset),
        parallel_offset(right, bottom, -inset),
        parallel_offset(bottom, left, -inset),
        parallel_offset(left, top, -inset),
    ]
    return edges, [top, right, bottom, left]


def get_redline_edges_cv(
    image: np.ndarray,
    tolerance: int = 25,
    inset: int = 0,
) -> list[list[PointTuple]]:
    """Return only the inset redline edges (backward-compatible wrapper)."""
    edges, _polygon = _redline_cv_geometry(image, tolerance, inset)
    return edges


class RedlineSegmenter:
    """Lazy Ultralytics segmentation wrapper for the redline mask."""

    def __init__(
        self,
        model_path: str,
        image_size: int = 736,
        confidence: float = 0.25,
        logger: LoggerPort | None = None,
    ) -> None:
        """Store model settings; the model loads on first prediction."""
        self._model_path = model_path
        self._image_size = image_size
        self._confidence = confidence
        self._logger = logger
        self._model: Any = None
        self._load_attempted = False

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _load(self) -> Any:
        """Load the YOLO model once."""
        if self._load_attempted:
            return self._model
        self._load_attempted = True
        path = Path(self._model_path).expanduser()
        if not path.is_absolute():
            path = get_project_paths().src_dir / path
        if not path.is_file():
            self._log("info", f"Redline model not found: {path}")
            return None
        try:
            from ultralytics import YOLO

            self._model = YOLO(str(path))
        except Exception as exc:
            self._log("warning", f"Cannot load redline model: {exc}")
            self._model = None
        return self._model

    def predict_polygon(self, image: np.ndarray) -> list[PointTuple]:
        """Return the largest ``base_area`` mask contour as a polygon."""
        model = self._load()
        if model is None:
            return []
        try:
            results = model.predict(
                source=image,
                imgsz=self._image_size,
                conf=self._confidence,
                verbose=False,
            )
        except Exception as exc:
            self._log("warning", f"Redline inference failed: {exc}")
            return []
        if not results:
            return []
        result = results[0]
        masks = getattr(result, "masks", None)
        if masks is None or len(getattr(masks, "data", [])) == 0:
            return []
        height, width = image.shape[:2]
        best_mask = None
        best_area = 0
        for tensor in masks.data:
            mask = tensor.detach().cpu().numpy()
            mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
            mask = (mask > 0.5).astype(np.uint8) * 255
            area = int(cv2.countNonZero(mask))
            if area > best_area:
                best_area = area
                best_mask = mask
        if best_mask is None or best_area < 500:
            return []
        contours, _ = cv2.findContours(
            best_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return []
        contour = max(contours, key=cv2.contourArea)
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.005 * perimeter, True)
        polygon = [(int(point[0][0]), int(point[0][1])) for point in approx]
        return polygon if len(polygon) >= 4 else []


class RedlineDetector:
    """Detect the redline polygon/edges from a captured frame."""

    def __init__(
        self,
        model_path: str = defaults.DEFAULT_YOLO_MODEL,
        image_size: int = 736,
        confidence: float = 0.25,
        offset_ratio: float = defaults.DEFAULT_REDLINE_OFFSET_RATIO,
        use_yolo: bool = True,
        logger: LoggerPort | None = None,
    ) -> None:
        """Create the detector; OpenCV remains the guaranteed fallback."""
        self._offset_ratio = offset_ratio
        self._use_yolo = use_yolo
        self._logger = logger
        self._segmenter = RedlineSegmenter(
            model_path,
            image_size=image_size,
            confidence=confidence,
            logger=logger,
        )

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def detect(self, frame: Frame) -> RedlineResult:
        """Return a redline result using YOLO when available, else OpenCV."""
        image = frame_image(frame)
        if image is None:
            return RedlineResult()
        if self._use_yolo:
            polygon = self._segmenter.predict_polygon(image)
            if polygon:
                edges = polygon_to_edges(polygon)
                if edges:
                    moved = offset_edges_to_outer(edges, ratio=0.0)
                    return RedlineResult(
                        polygon=tuple(Point(x, y) for x, y in polygon),
                        edges=tuple(tuple(Point(x, y) for x, y in edge) for edge in moved),
                        source="yolo",
                    )
                self._log("warning", "Redline polygon could not be split into edges")
        edges, polygon = _redline_cv_geometry(image)
        return RedlineResult(
            polygon=tuple(Point(x, y) for x, y in polygon),
            edges=tuple(tuple(Point(x, y) for x, y in edge) for edge in edges),
            source="cv",
        )
