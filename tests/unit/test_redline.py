"""Unit tests for redline detection geometry and fallback."""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from COCbot.core.vision.redline import (
    RedlineDetector,
    get_redline_edges_cv,
    polygon_to_edges,
    side_for_point,
)
from COCbot.models.frame import Frame


def redline_frame() -> Frame:
    """Return a synthetic 860x732 frame with a red diamond."""
    image = np.zeros((732, 860, 3), dtype=np.uint8)
    polygon = np.array(
        [[425, 150], [700, 345], [425, 540], [150, 345]],
        dtype=np.int32,
    )
    cv2.fillPoly(image, [polygon], (0, 0, 220))
    return Frame(image=image, width=860, height=732)


class RedlineGeometryTests(unittest.TestCase):
    """Verify side classification and polygon splitting."""

    def test_side_for_point(self) -> None:
        self.assertEqual(side_for_point(300, 300), "TL")
        self.assertEqual(side_for_point(500, 300), "TR")
        self.assertEqual(side_for_point(300, 450), "BL")
        self.assertEqual(side_for_point(500, 450), "BR")
        self.assertEqual(side_for_point(5, 5), "")

    def test_polygon_to_edges(self) -> None:
        polygon = [
            (425, 150),
            (520, 200),
            (700, 345),
            (560, 450),
            (425, 540),
            (290, 450),
            (150, 345),
            (250, 220),
            (360, 180),
            (400, 160),
        ]
        edges = polygon_to_edges(polygon)
        self.assertEqual(len(edges), 4)
        self.assertTrue(all(len(edge) >= 2 for edge in edges))


class RedlineDetectorTests(unittest.TestCase):
    """Verify the OpenCV fallback returns four usable edges."""

    def test_cv_fallback(self) -> None:
        frame = redline_frame()
        edges = get_redline_edges_cv(frame.image)
        self.assertEqual(len(edges), 4)
        self.assertTrue(all(len(edge) >= 3 for edge in edges))

        detector = RedlineDetector(use_yolo=False)
        result = detector.detect(frame)
        self.assertEqual(result.source, "cv")
        self.assertTrue(result.is_valid())
        midpoint = result.edge_midpoint(0)
        self.assertGreaterEqual(midpoint.x, 0)
        self.assertGreaterEqual(midpoint.y, 0)

    def test_missing_model_falls_back(self) -> None:
        detector = RedlineDetector(model_path="__missing_redline__.pt", use_yolo=True)
        result = detector.detect(redline_frame())
        self.assertEqual(result.source, "cv")
        self.assertTrue(result.is_valid())


if __name__ == "__main__":
    unittest.main()
