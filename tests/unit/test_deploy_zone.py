"""Unit tests for the deploy-zone ONNX redline integration.

The tests synthesize class maps (0/1/2) so they run without the 78 MB
model file or onnxruntime installed; only the pure numpy/opencv helpers
and the detector fallback chain are exercised.
"""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from COCbot.core.vision.redline import RedlineDetector
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point
from COCbot.vision.redline.deploy_zone import (
    DeployZonePolygonSource,
    DeployZonePrediction,
    mask_to_polygon,
    pick_deploy_points,
    redline_edges_from_cls,
    resample_polygon,
    sanitize_plan_edges,
)
from COCbot.vision.redline.detector import get_redline_edges_ex
from COCbot.vision.redline.yolo import polygon_to_edges

H, W = 732, 860


def synthetic_cls() -> np.ndarray:
    """Return a class map with a no-deploy ellipse and a deployable ring."""
    cls = np.zeros((H, W), np.uint8)
    angles = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    ellipse = np.array(
        [
            [int(433 + 200 * np.cos(a)), int(353 - 140 * np.sin(a))]
            for a in angles
        ],
        np.int32,
    )
    cv2.fillPoly(cls, [ellipse], 1)
    cls[640:, :] = 2  # interface strip along the bottom
    return cls


def synthetic_frame() -> Frame:
    """Return a frame with a red diamond for the OpenCV fallback."""
    image = np.zeros((H, W, 3), np.uint8)
    diamond = np.array(
        [[433, 180], [660, 353], [433, 525], [206, 353]], np.int32
    )
    cv2.fillPoly(image, [diamond], (0, 0, 220))
    return Frame(image=image, width=W, height=H)


class MaskConversionTests(unittest.TestCase):
    """Verify the no-deploy mask -> polygon -> edges chain."""

    def test_mask_to_polygon(self) -> None:
        polygon = mask_to_polygon(synthetic_cls())
        self.assertGreaterEqual(len(polygon), 4)
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        self.assertTrue(all(0 <= x < W for x in xs))
        self.assertTrue(all(0 <= y < H for y in ys))

    def test_empty_mask_has_no_polygon(self) -> None:
        self.assertEqual(mask_to_polygon(np.zeros((H, W), np.uint8)), [])
        self.assertEqual(mask_to_polygon(None), [])

    def test_tiny_mask_is_ignored(self) -> None:
        cls = np.zeros((H, W), np.uint8)
        cls[350:355, 430:436] = 1  # ~30 px, below MIN_MASK_AREA
        self.assertEqual(mask_to_polygon(cls), [])

    def test_interface_is_not_part_of_the_redline(self) -> None:
        polygon = mask_to_polygon(synthetic_cls())
        self.assertTrue(all(y < 640 for _x, y in polygon))

    def test_edges_from_cls(self) -> None:
        edges = redline_edges_from_cls(synthetic_cls())
        self.assertEqual(len(edges), 4)
        self.assertTrue(all(len(e) >= 2 for e in edges))

    def test_polygon_matches_yolo_edge_split(self) -> None:
        polygon = mask_to_polygon(synthetic_cls())
        resampled = resample_polygon(polygon)
        self.assertEqual(
            redline_edges_from_cls(synthetic_cls()), polygon_to_edges(resampled)
        )

    def test_straight_edges_survive_the_quadrant_split(self) -> None:
        # Regression (found on a real TH18 spread base): approxPolyDP keeps
        # only the endpoints of long straight sides, leaving a quadrant with
        # a single vertex. Resampling must repopulate every quadrant.
        cls = np.zeros((H, W), np.uint8)
        huge = np.array(
            [
                [430, 59], [790, 300], [700, 500], [430, 630],
                [150, 480], [128, 271],
            ],
            np.int32,
        )
        cv2.fillPoly(cls, [huge], 1)
        edges = redline_edges_from_cls(cls)
        self.assertEqual(len(edges), 4)
        self.assertTrue(all(len(e) >= 2 for e in edges))

    def test_resample_polygon_is_dense_and_closed(self) -> None:
        resampled = resample_polygon([(0, 0), (100, 0), (100, 100), (0, 100)], step_px=30)
        self.assertGreater(len(resampled), 4)
        self.assertIn((0, 0), resampled)
        gaps = [
            (resampled[i][0] - resampled[i - 1][0]) ** 2
            + (resampled[i][1] - resampled[i - 1][1]) ** 2
            for i in range(1, len(resampled))
        ]
        self.assertTrue(all(g <= (2 * 30) ** 2 for g in gaps))


class PickDeployPointsTests(unittest.TestCase):
    """Verify the SDK point picker on a synthetic ring."""

    def test_points_are_deployable_and_spread(self) -> None:
        cls = synthetic_cls()
        points = pick_deploy_points(cls, n=8, near_px=40, min_gap_px=25)
        self.assertGreaterEqual(len(points), 4)
        for x, y in points:
            self.assertEqual(int(cls[y, x]), 0)
        for i, (x, y) in enumerate(points):
            for px, py in points[i + 1:]:
                self.assertGreaterEqual((x - px) ** 2 + (y - py) ** 2, 25 ** 2)

    def test_empty_map_returns_no_points(self) -> None:
        interface_only = np.full((H, W), 2, np.uint8)
        self.assertEqual(pick_deploy_points(interface_only), [])

    def test_fully_deployable_map_falls_back_to_centre_points(self) -> None:
        deployable = np.zeros((H, W), np.uint8)
        self.assertEqual(len(pick_deploy_points(deployable, n=6)), 6)


class DetectorFallbackTests(unittest.TestCase):
    """Verify the onnx -> yolo -> cv priority chain without a model."""

    def test_missing_deploy_model_falls_back_to_cv(self) -> None:
        edges, source = get_redline_edges_ex(
            synthetic_frame().image,
            model_path="__missing_yolo__.pt",
            deploy_model_path="__missing_deploy__.onnx",
        )
        self.assertEqual(source, "cv")
        self.assertEqual(len(edges), 4)

    def test_invalid_frame_is_rejected(self) -> None:
        edges, source = get_redline_edges_ex(None, deploy_model_path="x.onnx")
        self.assertEqual((edges, source), (None, "none"))

    def test_injected_source_is_used_by_the_clean_detector(self) -> None:
        class FakeSource:
            source = "onnx"

            def predict_polygon(self, image):
                return mask_to_polygon(synthetic_cls())

        detector = RedlineDetector(use_yolo=True, segmenter=FakeSource())
        result = detector.detect(synthetic_frame())
        self.assertEqual(result.source, "onnx")
        self.assertTrue(result.is_valid())

    def test_injected_source_offsets_edges_into_the_deploy_band(self) -> None:
        # Regression: edges must move off the no-deploy boundary by the
        # configured offset ratio so taps land on legal ground.
        class OnnxSource:
            source = "onnx"

            def predict_polygon(self, image):
                return resample_polygon(mask_to_polygon(synthetic_cls()))

        detector = RedlineDetector(
            use_yolo=True, segmenter=OnnxSource(), offset_ratio=0.35
        )
        result = detector.detect(synthetic_frame())
        self.assertEqual(result.source, "onnx")
        self.assertTrue(result.is_valid())
        for edge in result.edges:
            self.assertGreaterEqual(len(edge), 3)
            for point in edge:
                self.assertFalse(result.contains(Point(point.x, point.y)))

    def test_clean_detector_still_falls_back_to_cv(self) -> None:
        detector = RedlineDetector(
            model_path="__missing_redline__.pt", use_yolo=True
        )
        result = detector.detect(synthetic_frame())
        self.assertEqual(result.source, "cv")
        self.assertTrue(result.is_valid())


class PolygonSourceTests(unittest.TestCase):
    """The adapter must degrade gracefully without the ONNX file."""

    def test_missing_model_is_not_ok(self) -> None:
        source = DeployZonePolygonSource("__missing_deploy__.onnx")
        self.assertFalse(source.ok)
        self.assertEqual(source.predict_polygon(synthetic_frame().image), [])


class SanitizePlanTests(unittest.TestCase):
    """Unsafe offset points must be nudged out or dropped before dropping."""

    def setUp(self) -> None:
        self.cls = synthetic_cls()
        self.prediction = DeployZonePrediction(
            self.cls, mask_to_polygon(self.cls), []
        )
        from COCbot.vision import redline  # noqa: F401  (module under test)
        from COCbot.vision.redline import deploy_zone
        self.deploy_zone = deploy_zone
        self._saved = deploy_zone._LAST_PREDICTION
        deploy_zone._LAST_PREDICTION = self.prediction

    def tearDown(self) -> None:
        self.deploy_zone._LAST_PREDICTION = self._saved

    def test_unsafe_points_are_nudged_or_dropped(self) -> None:
        edge = [(200, 353), (300, 200), (433, 353), (650, 353)]
        # (433, 353) sits inside the no-deploy ellipse -> must move/die.
        plan = {"edges": [edge]}
        self.deploy_zone.sanitize_plan_edges(plan)
        for x, y in plan["edges"][0]:
            self.assertEqual(int(self.cls[y, x]), 0)

    def test_plan_none_or_no_prediction_is_untouched(self) -> None:
        self.assertIsNone(self.deploy_zone.sanitize_plan_edges(None))
        self.deploy_zone._LAST_PREDICTION = None
        edge = [(433, 353)]
        plan = {"edges": [edge]}
        self.deploy_zone.sanitize_plan_edges(plan)
        self.assertEqual(plan["edges"][0], [(433, 353)])

    def test_interface_points_are_dropped_not_nudged(self) -> None:
        # Nudging deeper into the troop bar must never keep the point.
        edge = [(430, 660)]
        plan = {"edges": [edge]}
        self.deploy_zone.sanitize_plan_edges(plan)
        self.assertEqual(plan["edges"][0], [])


if __name__ == "__main__":
    unittest.main()
