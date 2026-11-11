"""Unit tests for template matching and OCR normalization."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from COCbot.core.errors import VisionError
from COCbot.core.vision.detector import DetectorConfig, YoloDetector
from COCbot.core.vision.image import imwrite
from COCbot.core.vision.ocr import NumberOcr, OcrConfig, normalize_digits
from COCbot.core.vision.templates import TemplateMatcher
from COCbot.models.frame import Frame
from COCbot.models.geometry import Rect


def patterned(height: int, width: int, seed: int = 7) -> np.ndarray:
    """Return a deterministic high-contrast BGR image."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(height, width, 3), dtype=np.uint8)


class TemplateMatcherTests(unittest.TestCase):
    """Verify exact-location matching and path safety."""

    def test_match_finds_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = patterned(20, 40, seed=11)
            self.assertTrue(imwrite(root / "button.png", template))

            frame_image = patterned(200, 220, seed=22)
            frame_image[80:100, 60:100] = template
            frame = Frame(image=frame_image, width=220, height=200)

            matcher = TemplateMatcher(root, default_threshold=0.99)
            match = matcher.match(frame, "button")
            self.assertIsNotNone(match)
            assert match is not None
            self.assertEqual((match.bbox.x1, match.bbox.y1), (60, 80))
            self.assertEqual(match.bbox.width, 40)
            self.assertEqual(match.bbox.height, 20)

    def test_match_respects_region(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = patterned(10, 10, seed=3)
            imwrite(root / "dot.png", template)
            frame_image = patterned(100, 100, seed=4)
            frame_image[50:60, 50:60] = template
            frame = Frame(image=frame_image, width=100, height=100)
            matcher = TemplateMatcher(root, default_threshold=0.99)
            match = matcher.match(frame, "dot", region=Rect(40, 40, 40, 40))
            self.assertIsNotNone(match)
            assert match is not None
            self.assertEqual((match.bbox.x1, match.bbox.y1), (50, 50))

    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            matcher = TemplateMatcher(Path(temp_dir))
            with self.assertRaises(VisionError):
                matcher.resolve("../outside.png")


class OcrTests(unittest.TestCase):
    """Verify digit cleanup and graceful failure without an engine."""

    def test_normalize_digits(self) -> None:
        self.assertEqual(normalize_digits("1O2o3"), "10203")
        self.assertEqual(normalize_digits("abc"), "")
        self.assertEqual(normalize_digits("12,345"), "12345")

    def test_unavailable_tesseract_returns_none(self) -> None:
        image = np.full((30, 80, 3), 255, dtype=np.uint8)
        ocr = NumberOcr(
            OcrConfig(
                engine="tesseract",
                tesseract_cmd="__definitely_missing_tesseract__",
            )
        )
        self.assertIsNone(ocr.read_number(image))
        self.assertIsNone(ocr.read_number(Frame(image=image, width=80, height=30)))


class DetectorTests(unittest.TestCase):
    """Verify a missing YOLO model degrades gracefully."""

    def test_missing_model_returns_no_detections(self) -> None:
        detector = YoloDetector(DetectorConfig(model_path="__missing_model__.pt"))
        self.assertFalse(detector.is_available)
        frame = Frame(image=np.zeros((10, 10, 3), dtype=np.uint8), width=10, height=10)
        self.assertEqual(list(detector.detect(frame)), [])


if __name__ == "__main__":
    unittest.main()
