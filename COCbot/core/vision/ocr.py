"""Numeric OCR for resource and loot labels.

Engine order: PaddleOCR first (best accuracy on CoC digits), then Tesseract
with a white-digit mask. Both engines are lazy-loaded, so importing this module
does not start Paddle or torch.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from COCbot.core.config import defaults
from COCbot.core.ports import LoggerPort
from COCbot.core.vision.image import crop, frame_image, resize_scale
from COCbot.models.frame import Frame
from COCbot.models.geometry import Rect


@dataclass(frozen=True)
class OcrConfig:
    """OCR engine selection and preprocessing options."""

    engine: str = "auto"
    tesseract_cmd: str = defaults.DEFAULT_TESSERACT_CMD
    max_value: int = defaults.DEFAULT_OCR_MAX_VALUE
    upsample: int = defaults.DEFAULT_OCR_UPSCALE

    def __post_init__(self) -> None:
        """Normalize the engine name."""
        object.__setattr__(self, "engine", str(self.engine or "auto").lower())


def normalize_digits(text: str) -> str:
    """Keep only digits, repairing the common ``O``/``o`` OCR confusion."""
    cleaned = (text or "").replace("O", "0").replace("o", "0")
    return re.sub(r"\D", "", cleaned)


class NumberOcr:
    """Read integers from screenshots or image crops."""

    def __init__(
        self,
        config: OcrConfig | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Create an OCR adapter; engines load on first use."""
        self._config = config or OcrConfig()
        self._logger = logger
        self._paddle: Any = None
        self._paddle_checked = False
        self._lock = threading.RLock()

    @property
    def config(self) -> OcrConfig:
        """Return the immutable OCR configuration."""
        return self._config

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _get_paddle(self) -> Any:
        """Return a shared PaddleOCR engine, or ``None`` when unavailable."""
        with self._lock:
            if self._paddle_checked:
                return self._paddle
            self._paddle_checked = True
            if self._config.engine == "tesseract":
                return None
            try:
                from paddleocr import PaddleOCR

                self._paddle = PaddleOCR(
                    text_detection_model_name=None,
                    text_recognition_model_name="PP-OCRv6_small_rec",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    enable_mkldnn=False,
                    lang="en",
                )
            except Exception as exc:
                self._paddle = None
                self._log("warning", f"PaddleOCR unavailable: {type(exc).__name__}: {exc}")
            return self._paddle

    def _read_paddle(self, image: np.ndarray) -> str:
        """Read digits with PaddleOCR."""
        engine = self._get_paddle()
        if engine is None:
            return ""
        upscaled = resize_scale(image, float(self._config.upsample))
        try:
            with self._lock:
                results = engine.predict(upscaled)
        except Exception as exc:
            self._log("warning", f"Paddle inference failed: {exc}")
            return ""

        chunks: list[str] = []
        for result in results or []:
            texts = getattr(result, "rec_texts", None)
            if texts is None and hasattr(result, "get"):
                texts = result.get("rec_texts", [])
            for text in texts or []:
                digits = normalize_digits(str(text))
                if digits:
                    chunks.append(digits)
        return "".join(chunks)

    def _prep_tesseract(self, image: np.ndarray) -> np.ndarray:
        """Convert white game digits to black text on a white background."""
        upscaled = resize_scale(image, float(self._config.upsample))
        blue, green, red = cv2.split(upscaled)
        mask = ((blue > 190) & (green > 190) & (red > 190)).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        inverted = 255 - mask
        return cv2.copyMakeBorder(
            inverted, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
        )

    def _read_tesseract(self, image: np.ndarray) -> str:
        """Read digits with Tesseract as a fallback."""
        if self._config.engine == "paddle":
            return ""
        try:
            import pytesseract
        except Exception:
            return ""
        if self._config.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self._config.tesseract_cmd

        prepared = self._prep_tesseract(image)
        best = ""
        for psm in (7, 8, 6, 13):
            try:
                text = pytesseract.image_to_string(
                    prepared,
                    config=(
                        f"--oem 1 --psm {psm} "
                        "-c tessedit_char_whitelist=0123456789"
                    ),
                )
            except Exception:
                continue
            digits = normalize_digits(text)
            if len(digits) > len(best):
                best = digits
        return best

    def read_digits(self, image: np.ndarray) -> str:
        """Return the digit string in *image* (may be empty)."""
        if image is None or getattr(image, "size", 0) == 0:
            return ""
        digits = self._read_paddle(image)
        if digits:
            return digits
        return self._read_tesseract(image)

    def read_number(
        self,
        frame: Frame | np.ndarray,
        region: Rect | None = None,
        max_value: int | None = None,
    ) -> int | None:
        """Read an integer from a frame or image crop."""
        image = frame_image(frame) if isinstance(frame, Frame) else frame
        if image is None or getattr(image, "size", 0) == 0:
            return None
        if region is not None:
            image = crop(image, region)
            if image.size == 0:
                return None
        digits = self.read_digits(image)
        if not digits:
            return None
        value = int(digits)
        limit = self._config.max_value if max_value is None else int(max_value)
        return value if value <= limit else None
