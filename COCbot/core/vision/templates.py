"""Template matching against the bundled ``Templates`` directory."""

from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from COCbot.core.config.paths import get_project_paths
from COCbot.core.errors import VisionError
from COCbot.core.ports import LoggerPort
from COCbot.core.vision.image import crop, frame_image, imread, to_gray
from COCbot.models.attack import Detection
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Rect


class TemplateMatcher:
    """Load and match PNG templates with a bounded cache."""

    def __init__(
        self,
        templates_dir: Path | str | None = None,
        default_threshold: float = 0.88,
        logger: LoggerPort | None = None,
    ) -> None:
        """Create a matcher rooted at *templates_dir*."""
        self._dir = Path(templates_dir) if templates_dir else get_project_paths().templates_dir
        self._threshold = float(default_threshold)
        self._logger = logger
        self._cache: dict[str, np.ndarray] = {}
        self._lock = threading.RLock()

    @property
    def templates_dir(self) -> Path:
        """Return the template root directory."""
        return self._dir

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def resolve(self, name: str) -> Path:
        """Resolve *name* inside the template root and reject escapes."""
        candidate = self._dir / name
        if not candidate.suffix:
            candidate = candidate.with_suffix(".png")
        resolved = candidate.resolve()
        root = self._dir.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise VisionError(f"template escapes root: {name}") from exc
        return resolved

    def load(self, name: str) -> np.ndarray | None:
        """Load a template once and cache its grayscale version."""
        with self._lock:
            if name in self._cache:
                return self._cache[name]
            path = self.resolve(name)
            image = imread(path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                self._log("warning", f"Template not found or unreadable: {path}")
                return None
            self._cache[name] = image
            return image

    def clear_cache(self) -> None:
        """Drop every cached template."""
        with self._lock:
            self._cache.clear()

    def score(
        self,
        frame: Frame,
        name: str,
        region: Rect | None = None,
    ) -> float:
        """Return the best match score for *name* in *frame*."""
        image = frame_image(frame)
        template = self.load(name)
        if image is None or template is None:
            return 0.0
        gray = to_gray(image)
        if region is not None:
            gray = crop(gray, region)
        if (
            gray.size == 0
            or gray.shape[0] < template.shape[0]
            or gray.shape[1] < template.shape[1]
        ):
            return 0.0
        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_value, _, _ = cv2.minMaxLoc(result)
        if not math.isfinite(max_value):
            return 0.0
        return float(max_value)

    def match(
        self,
        frame: Frame,
        name: str,
        region: Rect | None = None,
        threshold: float | None = None,
    ) -> Detection | None:
        """Return the best match above the threshold, or ``None``."""
        matches = self.match_all(frame, name, region=region, threshold=threshold, limit=1)
        return matches[0] if matches else None

    def match_all(
        self,
        frame: Frame,
        name: str,
        region: Rect | None = None,
        threshold: float | None = None,
        limit: int = 20,
    ) -> Sequence[Detection]:
        """Return non-overlapping matches sorted by confidence."""
        image = frame_image(frame)
        template = self.load(name)
        if image is None or template is None:
            return []
        gray = to_gray(image)
        offset_x = 0
        offset_y = 0
        if region is not None:
            gray = crop(gray, region)
            offset_x, offset_y = region.x, region.y
        if (
            gray.size == 0
            or gray.shape[0] < template.shape[0]
            or gray.shape[1] < template.shape[1]
        ):
            return []

        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        minimum = self._threshold if threshold is None else float(threshold)
        ys, xs = np.where(result >= minimum)
        if len(xs) == 0:
            return []

        height, width = template.shape[:2]
        candidates: list[Detection] = []
        for x, y in zip(xs, ys):
            score = float(result[y, x])
            if not math.isfinite(score):
                continue
            bbox = BoundingBox(
                int(x) + offset_x,
                int(y) + offset_y,
                int(x) + offset_x + width,
                int(y) + offset_y + height,
            )
            candidates.append(Detection(label=name, confidence=score, bbox=bbox))
        candidates.sort(key=lambda item: item.confidence, reverse=True)

        selected: list[Detection] = []
        for candidate in candidates:
            if all(candidate.bbox.iou(kept.bbox) < 0.3 for kept in selected):
                selected.append(candidate)
            if len(selected) >= limit:
                break
        return selected
