"""Unit tests for screenshot capture and image helpers."""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from COCbot.core.vision.capture import (
    CaptureConfig,
    ScreenCapture,
    decode_framebuffer,
)
from COCbot.core.vision.image import decode_image, is_blank, to_gray
from COCbot.models.frame import Frame


def encode(image: np.ndarray) -> bytes:
    """Encode a BGR array as PNG bytes."""
    success, buffer = cv2.imencode(".png", image)
    assert success
    return buffer.tobytes()


def noisy_image(height: int = 70, width: int = 90) -> np.ndarray:
    """Return a deterministic non-blank BGR image."""
    rng = np.random.default_rng(1234)
    return rng.integers(0, 255, size=(height, width, 3), dtype=np.uint8)


class FakeAdb:
    """Return scripted screenshot payloads."""

    def __init__(self, payloads: list[bytes | None]) -> None:
        self.payloads = payloads
        self.calls = 0

    def screenshot(self) -> bytes | None:
        self.calls += 1
        if not self.payloads:
            return None
        return self.payloads.pop(0)


class CaptureTests(unittest.TestCase):
    """Verify retries, validation, and raw-byte preservation."""

    def test_capture_returns_frame(self) -> None:
        image = noisy_image()
        payload = encode(image)
        adb = FakeAdb([payload])
        capture = ScreenCapture(adb, CaptureConfig(max_retries=1, retry_delay=0))
        frame = capture.capture()
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.width, 90)
        self.assertEqual(frame.height, 70)
        self.assertEqual(frame.raw, payload)
        self.assertFalse(frame.is_empty())

    def test_blank_frame_is_rejected(self) -> None:
        blank = np.zeros((50, 60, 3), dtype=np.uint8)
        adb = FakeAdb([encode(blank)])
        failures: list[bool] = []
        capture = ScreenCapture(
            adb,
            CaptureConfig(max_retries=1, retry_delay=0),
            on_failure=lambda: failures.append(True),
        )
        self.assertIsNone(capture.capture())
        self.assertEqual(failures, [True])

    def test_retries_after_missing_data(self) -> None:
        payload = encode(noisy_image())
        adb = FakeAdb([None, payload])
        capture = ScreenCapture(adb, CaptureConfig(max_retries=2, retry_delay=0))
        frame = capture.capture()
        self.assertIsNotNone(frame)
        self.assertEqual(adb.calls, 2)

    def test_image_helpers(self) -> None:
        image = noisy_image(10, 20)
        self.assertIsNotNone(decode_image(encode(image)))
        self.assertFalse(is_blank(image))
        self.assertEqual(to_gray(image).shape, (10, 20))
        self.assertTrue(is_blank(np.zeros((5, 5, 3), dtype=np.uint8)))

    def test_frame_is_empty_checks_none_and_size(self) -> None:
        frame = Frame(image="not-an-image", width=1, height=1)
        self.assertFalse(frame.is_empty())

    def test_decode_framebuffer_rgba(self) -> None:
        import struct

        pixels = np.zeros((2, 2, 4), dtype=np.uint8)
        pixels[0, 0] = (255, 0, 0, 255)   # red
        pixels[0, 1] = (0, 255, 0, 255)   # green
        pixels[1, 0] = (0, 0, 255, 255)   # blue
        pixels[1, 1] = (255, 255, 255, 255)
        payload = struct.pack("<III", 2, 2, 1) + pixels.tobytes()
        image = decode_framebuffer(payload)
        self.assertIsNotNone(image)
        assert image is not None
        self.assertEqual(image.shape, (2, 2, 3))
        self.assertEqual(tuple(image[0, 0]), (0, 0, 255))
        self.assertEqual(tuple(image[1, 0]), (255, 0, 0))

    def test_capture_prefers_raw_framebuffer(self) -> None:
        import struct

        rng = np.random.default_rng(7)
        pixels = rng.integers(0, 255, size=(70, 90, 4), dtype=np.uint8)
        payload = struct.pack("<III", 90, 70, 1) + pixels.tobytes()

        class RawAdb:
            def __init__(self) -> None:
                self.raw_calls = 0
                self.png_calls = 0

            def screenshot_raw(self) -> bytes:
                self.raw_calls += 1
                return payload

            def screenshot(self) -> bytes | None:
                self.png_calls += 1
                return None

        adb = RawAdb()
        capture = ScreenCapture(adb, CaptureConfig(max_retries=1, retry_delay=0))
        frame = capture.capture()
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual((frame.width, frame.height), (90, 70))
        self.assertEqual(adb.raw_calls, 1)
        self.assertEqual(adb.png_calls, 0)

    def test_capture_falls_back_to_png_when_raw_is_junk(self) -> None:
        payload = encode(noisy_image())
        adb = FakeAdb([payload])
        adb.screenshot_raw = lambda: b"junk"  # type: ignore[attr-defined]
        capture = ScreenCapture(adb, CaptureConfig(max_retries=1, retry_delay=0))
        frame = capture.capture()
        self.assertIsNotNone(frame)
        self.assertEqual(adb.calls, 1)


if __name__ == "__main__":
    unittest.main()
