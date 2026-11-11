"""Home-village resource and builder readouts for the shell.

Coordinates are calibrated for the 860x732 MEmu frame used everywhere else in
the project: the four currency counters sit in the top-right corner and the
builder/lab counters sit just above the Build button.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np

from COCbot.core.ports import CapturePort, LoggerPort
from COCbot.core.vision.image import frame_image
from COCbot.models.frame import Frame
from COCbot.models.geometry import Rect

HOME_GOLD_REGION = Rect(660, 12, 168, 34)
HOME_ELIXIR_REGION = Rect(660, 45, 168, 35)
HOME_DARK_REGION = Rect(660, 79, 168, 35)
HOME_GEMS_REGION = Rect(685, 110, 130, 42)
# "5/5" builders and "1/2" researchers, above the Build button.
HOME_BUILDERS_REGION = Rect(740, 596, 64, 40)

MAX_RESOURCE = 100_000_000
MAX_GEMS = 10_000_000
MAX_BUILDERS = 10


@dataclass(frozen=True)
class VillageResources:
    """One snapshot of the home-village counters."""

    gold: int | None = None
    elixir: int | None = None
    dark_elixir: int | None = None
    gems: int | None = None
    builders_available: int | None = None
    builders_total: int | None = None

    def has_values(self) -> bool:
        """Return ``True`` when at least one counter was read."""
        return any(
            value is not None
            for value in (
                self.gold,
                self.elixir,
                self.dark_elixir,
                self.gems,
                self.builders_available,
            )
        )


def _digits(text: str) -> str:
    """Return only the digits of *text*."""
    return "".join(ch for ch in text if ch.isdigit())


def _prepare(image: np.ndarray) -> np.ndarray:
    """Convert white game digits to black text on a white background."""
    upscaled = cv2.resize(
        image,
        None,
        fx=6,
        fy=6,
        interpolation=cv2.INTER_CUBIC,
    )
    if upscaled.ndim == 3:
        blue, green, red = cv2.split(upscaled)
        mask = ((blue > 190) & (green > 190) & (red > 190)).astype(np.uint8) * 255
    else:
        mask = (upscaled > 190).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    inverted = 255 - mask
    return cv2.copyMakeBorder(inverted, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)


def _ocr_text(prepared: np.ndarray, whitelist: str, psm: int) -> str:
    """Run one Tesseract pass on a prepared image."""
    import pytesseract

    return pytesseract.image_to_string(
        prepared,
        config=f"--oem 1 --psm {psm} -c tessedit_char_whitelist={whitelist}",
    )


def ocr_number(image: np.ndarray) -> int | None:
    """Read one integer from a counter crop with Tesseract only."""
    try:
        import pytesseract  # noqa: F401
    except Exception:
        return None
    if image is None or getattr(image, "size", 0) == 0:
        return None
    prepared = _prepare(image)
    best = ""
    for psm in (7, 8, 6, 13):
        try:
            value = _digits(_ocr_text(prepared, "0123456789", psm))
        except Exception:
            continue
        if len(value) > len(best):
            best = value
    return int(best) if best else None


def ocr_fraction(image: np.ndarray) -> tuple[int, int] | None:
    """Read an ``available/total`` counter such as ``5/5``."""
    try:
        import pytesseract  # noqa: F401
    except Exception:
        return None
    if image is None or getattr(image, "size", 0) == 0:
        return None
    prepared = _prepare(image)
    text = ""
    for psm in (7, 6, 8):
        try:
            text = _ocr_text(prepared, "0123456789/", psm)
        except Exception:
            continue
        if "/" in text:
            break
    if "/" in text:
        left, right = text.split("/", 1)
        left_digits, right_digits = _digits(left), _digits(right)
        if left_digits and right_digits:
            return (int(left_digits), int(right_digits))
    digits = _digits(text)
    if len(digits) < 2:
        return None
    half = len(digits) // 2
    return (int(digits[:half]), int(digits[half:]))


class ResourceReader:
    """Capture the home village and read its counters."""

    def __init__(
        self,
        capture: CapturePort,
        logger: LoggerPort | None = None,
        number_reader: Callable[[np.ndarray], int | None] | None = None,
        fraction_reader: Callable[[np.ndarray], tuple[int, int] | None] | None = None,
    ) -> None:
        """Create the reader with optional injected OCR callables."""
        self._capture = capture
        self._logger = logger
        self._read_number = number_reader or ocr_number
        self._read_fraction = fraction_reader or ocr_fraction

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    @staticmethod
    def _crop(frame: Frame, region: Rect) -> np.ndarray | None:
        """Return the pixel crop for *region*."""
        image = frame_image(frame)
        if image is None:
            return None
        crop = image[region.y : region.bottom, region.x : region.right]
        return crop if crop.size else None

    def _number(self, frame: Frame, region: Rect, maximum: int) -> int | None:
        """Read a bounded counter from one region."""
        crop = self._crop(frame, region)
        if crop is None:
            return None
        value = self._read_number(crop)
        if value is None or value < 0 or value > maximum:
            return None
        return value

    def _builders(self, frame: Frame) -> tuple[int | None, int | None]:
        """Read the builder counter above the Build button."""
        crop = self._crop(frame, HOME_BUILDERS_REGION)
        if crop is None:
            return (None, None)
        result = self._read_fraction(crop)
        if result is None:
            return (None, None)
        available, total = result
        if total <= 0 or total > MAX_BUILDERS or available > total:
            return (None, None)
        return (available, total)

    def read(self) -> VillageResources:
        """Return one snapshot; unreadable counters stay ``None``."""
        frame = self._capture.capture()
        if frame is None:
            return VillageResources()
        builders_available, builders_total = self._builders(frame)
        snapshot = VillageResources(
            gold=self._number(frame, HOME_GOLD_REGION, MAX_RESOURCE),
            elixir=self._number(frame, HOME_ELIXIR_REGION, MAX_RESOURCE),
            dark_elixir=self._number(frame, HOME_DARK_REGION, MAX_RESOURCE),
            gems=self._number(frame, HOME_GEMS_REGION, MAX_GEMS),
            builders_available=builders_available,
            builders_total=builders_total,
        )
        if not snapshot.has_values():
            self._log("debug", "Resource readout found no counters on screen")
        return snapshot
