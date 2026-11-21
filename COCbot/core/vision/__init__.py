"""Vision infrastructure: image helpers, capture, OCR, and templates."""

from COCbot.core.vision.capture import CaptureConfig, ScreenCapture
from COCbot.core.vision.image import (
    crop,
    decode_image,
    encode_png,
    frame_image,
    imread,
    imwrite,
    is_blank,
    resize_scale,
    to_gray,
)
from COCbot.core.vision.ocr import NumberOcr, OcrConfig, normalize_digits
from COCbot.core.vision.templates import TemplateMatcher

__all__ = [
    "CaptureConfig",
    "NumberOcr",
    "OcrConfig",
    "ScreenCapture",
    "TemplateMatcher",
    "crop",
    "decode_image",
    "encode_png",
    "frame_image",
    "imread",
    "imwrite",
    "is_blank",
    "normalize_digits",
    "resize_scale",
    "to_gray",
]
