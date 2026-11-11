"""Ultralytics YOLO detector adapter.

The model is loaded lazily so importing the GUI never pays the torch/Ultralytics
startup cost. Missing models degrade to an empty detection list instead of
crashing the bot.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from COCbot.core.config import defaults
from COCbot.core.config.paths import get_project_paths
from COCbot.core.ports import LoggerPort
from COCbot.core.vision.image import frame_image
from COCbot.models.attack import Detection
from COCbot.models.frame import Frame
from COCbot.models.geometry import BoundingBox, Point


@dataclass(frozen=True)
class DetectorConfig:
    """Model and inference settings."""

    model_path: str = defaults.DEFAULT_YOLO_MODEL
    confidence: float = defaults.DEFAULT_YOLO_CONFIDENCE
    iou: float = defaults.DEFAULT_YOLO_IOU
    image_size: int = 736
    device: str | None = None


class YoloDetector:
    """YOLOv8/YOLO11 segmentation adapter implementing ``DetectorPort``."""

    def __init__(
        self,
        config: DetectorConfig | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Create a detector; the model is loaded on first use."""
        self._config = config or DetectorConfig()
        self._logger = logger
        self._model: Any = None
        self._load_attempted = False
        self._load_error = ""
        self._lock = threading.RLock()

    @property
    def config(self) -> DetectorConfig:
        """Return the immutable detector configuration."""
        return self._config

    @property
    def is_available(self) -> bool:
        """Return ``True`` when the model file exists and loads."""
        return self._load_model() is not None

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _resolve_model_path(self) -> Path:
        """Resolve the configured model path against the project root."""
        raw = Path(self._config.model_path).expanduser()
        if raw.is_absolute():
            return raw
        return get_project_paths().src_dir / raw

    def _load_model(self) -> Any:
        """Load the Ultralytics model once and cache it."""
        with self._lock:
            if self._load_attempted:
                return self._model
            self._load_attempted = True
            path = self._resolve_model_path()
            if not path.is_file():
                self._load_error = f"model not found: {path}"
                self._log("warning", self._load_error)
                return None
            try:
                from ultralytics import YOLO
            except Exception as exc:
                self._load_error = f"ultralytics unavailable: {exc}"
                self._log("warning", self._load_error)
                return None
            try:
                self._model = YOLO(str(path))
            except Exception as exc:
                self._load_error = f"cannot load YOLO model: {exc}"
                self._log("error", self._load_error)
                self._model = None
            return self._model

    @staticmethod
    def _label_for(names: Any, class_id: int) -> str:
        """Resolve a class id to a human-readable label."""
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        try:
            return str(names[class_id])
        except (IndexError, KeyError, TypeError):
            return str(class_id)

    def detect(
        self,
        frame: Frame,
        confidence: float | None = None,
    ) -> Sequence[Detection]:
        """Run inference on *frame* and return clamped detections."""
        image = frame_image(frame)
        if image is None:
            return []
        model = self._load_model()
        if model is None:
            return []

        threshold = self._config.confidence if confidence is None else float(confidence)
        kwargs: dict[str, Any] = {
            "source": image,
            "imgsz": self._config.image_size,
            "conf": threshold,
            "iou": self._config.iou,
            "verbose": False,
        }
        if self._config.device:
            kwargs["device"] = self._config.device

        try:
            with self._lock:
                results = model.predict(**kwargs)
        except Exception as exc:
            self._log("error", f"YOLO inference failed: {exc}")
            return []

        if not results:
            return []
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []

        names = getattr(result, "names", getattr(model, "names", {}))
        coordinates = boxes.xyxy.detach().cpu().numpy()
        scores = boxes.conf.detach().cpu().numpy()
        classes = boxes.cls.detach().cpu().numpy()

        masks = getattr(result, "masks", None)
        polygons = list(getattr(masks, "xy", []) or []) if masks is not None else []

        height, width = image.shape[:2]
        detections: list[Detection] = []
        for index, (coords, score, class_id) in enumerate(
            zip(coordinates, scores, classes)
        ):
            x1, y1, x2, y2 = (int(round(float(value))) for value in coords[:4])
            x1 = max(0, min(width, x1))
            y1 = max(0, min(height, y1))
            x2 = max(0, min(width, x2))
            y2 = max(0, min(height, y2))
            if x2 <= x1 or y2 <= y1:
                continue
            polygon: tuple[Point, ...] = ()
            if index < len(polygons):
                polygon = tuple(
                    Point(int(round(float(px))), int(round(float(py))))
                    for px, py in polygons[index]
                )
            detections.append(
                Detection(
                    label=self._label_for(names, int(class_id)),
                    confidence=float(score),
                    bbox=BoundingBox(x1, y1, x2, y2),
                    polygon=polygon,
                )
            )
        return detections
