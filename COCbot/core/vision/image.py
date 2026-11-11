"""Image helpers that are safe with Unicode Windows paths."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from COCbot.models.frame import Frame
from COCbot.models.geometry import Rect


def decode_image(data: bytes, flags: int = cv2.IMREAD_COLOR) -> np.ndarray | None:
    """Decode encoded image bytes into a BGR array."""
    if not data:
        return None
    buffer = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(buffer, flags)


def imread(path: Path | str, flags: int = cv2.IMREAD_COLOR) -> np.ndarray | None:
    """Read an image from a possibly non-ASCII path."""
    try:
        buffer = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None
    if buffer.size == 0:
        return None
    return cv2.imdecode(buffer, flags)


def imwrite(path: Path | str, image: np.ndarray) -> bool:
    """Write an image to a possibly non-ASCII path."""
    suffix = Path(path).suffix or ".png"
    success, encoded = cv2.imencode(suffix, image)
    if not success:
        return False
    try:
        encoded.tofile(str(path))
    except OSError:
        return False
    return True


def encode_png(image: np.ndarray) -> bytes:
    """Encode a BGR array as PNG bytes."""
    success, encoded = cv2.imencode(".png", image)
    return encoded.tobytes() if success else b""


def to_gray(image: np.ndarray) -> np.ndarray:
    """Return a grayscale view of a BGR image."""
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def crop(image: np.ndarray, rect: Rect) -> np.ndarray:
    """Crop *rect* from *image* and return an empty array when out of bounds."""
    height, width = image.shape[:2]
    clipped = rect.clamp(Rect(0, 0, width, height))
    return image[clipped.y : clipped.bottom, clipped.x : clipped.right]


def resize_scale(image: np.ndarray, scale: float) -> np.ndarray:
    """Resize by a uniform *scale* factor."""
    if scale <= 0 or scale == 1.0:
        return image
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def is_blank(image: np.ndarray, min_stddev: float = 1.0) -> bool:
    """Return ``True`` when the image is (nearly) a single flat colour."""
    if image is None or image.size == 0:
        return True
    gray = to_gray(image)
    _, stddev = cv2.meanStdDev(gray)
    return float(stddev[0][0]) < min_stddev


def frame_image(frame: Frame) -> np.ndarray | None:
    """Return the underlying BGR array when it is usable."""
    image = frame.image
    if not isinstance(image, np.ndarray) or image.size == 0:
        return None
    return image
