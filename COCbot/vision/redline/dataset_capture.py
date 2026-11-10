"""Auto-capture screenshots for YOLO-seg redline training.

Design goals:
- Do not slow down the attack loop: encoding/writes happen on a daemon thread.
- Active learning: capture 100% of OpenCV fallback frames, sample a small
  fraction of successful YOLO frames.
- Avoid duplicates with an MD5 of the stored bytes.
- Respect a hard max file count so the dataset cannot grow without bound.
- Keep storage small: JPEG (default) or WebP instead of the 1.4 MB ADB PNG.

Output (example with auto_capture_format = "jpg"):
  datasets/redline/images/raw/auto_YYYY-MM-DD_HH-MM-SS_<tag>_<n>.jpg
  datasets/redline/images/raw/auto_...jpg.json   (metadata sidecar)

Label files are separate:
  datasets/redline/labels/raw/auto_...txt
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import random
import threading
import time
from datetime import datetime

import cv2

_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# _ROOT is the project root (src/), i.e. four levels up from this file:
# src/COCbot/vision/redline/dataset_capture.py -> src

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def _default_dir() -> str:
    return os.path.join(_ROOT, "datasets", "redline", "images", "raw")


def _resolve_dir(path: str) -> str:
    if not path:
        return _default_dir()
    if os.path.isabs(path):
        return path
    return os.path.join(_ROOT, path)


def _normalize_format(value: str) -> str:
    fmt = (value or "jpg").lower().lstrip(".")
    if fmt in ("jpeg", "jpg"):
        return "jpg"
    if fmt == "webp":
        return "webp"
    return "png"


class DatasetCapture:
    def __init__(self, enabled: bool = False, out_dir: str = "",
                 min_interval_sec: float = 2.0, max_files: int = 2000,
                 only_on_fallback: bool = True, success_sample: float = 0.1,
                 scout_sample: float = 1.0, capture_on_scout: bool = True,
                 capture_on_attack: bool = True, save_json: bool = True,
                 image_format: str = "jpg", jpeg_quality: int = 92,
                 webp_quality: int = 90, png_compression: int = 9):
        self.enabled = bool(enabled)
        self.out_dir = _resolve_dir(out_dir)
        self.min_interval_sec = max(0.0, float(min_interval_sec))
        self.max_files = max(0, int(max_files))
        self.only_on_fallback = bool(only_on_fallback)
        self.success_sample = max(0.0, min(1.0, float(success_sample)))
        self.scout_sample = max(0.0, min(1.0, float(scout_sample)))
        self.capture_on_scout = bool(capture_on_scout)
        self.capture_on_attack = bool(capture_on_attack)
        self.save_json = bool(save_json)
        self.image_format = _normalize_format(image_format)
        self.jpeg_quality = max(1, min(100, int(jpeg_quality)))
        self.webp_quality = max(1, min(100, int(webp_quality)))
        self.png_compression = max(0, min(9, int(png_compression)))

        self._last_time = 0.0
        self._count = 0
        self._hashes = set()
        self._lock = threading.Lock()
        self._queue = queue.Queue(maxsize=8)
        self._worker = None

        if self.enabled:
            os.makedirs(self.out_dir, exist_ok=True)
            self._count = sum(
                1 for n in os.listdir(self.out_dir)
                if n.lower().endswith(IMAGE_EXTS)
            )
            self._worker = threading.Thread(
                target=self._run, name="redline-dataset-capture", daemon=True)
            self._worker.start()
            print(f"[CAPTURE] dataset auto-capture -> {self.out_dir} "
                  f"(fmt={self.image_format}, existing={self._count}, "
                  f"max={self.max_files})")

    def _run(self):
        while True:
            item = self._queue.get()
            if item is None:
                return
            path, data, meta = item
            try:
                with open(path, "wb") as f:
                    f.write(data)
                if self.save_json and meta is not None:
                    with open(path + ".json", "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[CAPTURE] write failed: {e}")

    def _encode(self, img):
        """Return (bytes, extension) for the configured format."""
        if self.image_format == "png":
            raw = getattr(img, "png_bytes", None)
            if raw:
                return raw, ".png"
            ok, buf = cv2.imencode(
                ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, self.png_compression])
            return (buf.tobytes(), ".png") if ok else (None, "")

        if self.image_format == "webp":
            ok, buf = cv2.imencode(
                ".webp", img, [cv2.IMWRITE_WEBP_QUALITY, self.webp_quality])
            return (buf.tobytes(), ".webp") if ok else (None, "")

        ok, buf = cv2.imencode(
            ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        return (buf.tobytes(), ".jpg") if ok else (None, "")

    def _should_capture(self, source: str) -> bool:
        if not self.enabled:
            return False
        if self.max_files and self._count >= self.max_files:
            return False

        now = time.time()
        if self._last_time and now - self._last_time < self.min_interval_sec:
            return False

        source = (source or "unknown").lower()

        # Scout / resource-comparison frames: base fully visible, no attack
        # effects. This is the primary dataset source.
        if source in ("scout", "loot", "resource"):
            if not self.capture_on_scout or self.scout_sample <= 0:
                return False
            return random.random() <= self.scout_sample

        # Attack frames.
        if not self.capture_on_attack:
            return False
        if source == "yolo":
            if self.success_sample <= 0:
                return False
            if random.random() > self.success_sample:
                return False
        else:
            # cv fallback / no model: capture all (active learning).
            if self.only_on_fallback is False and self.success_sample <= 0:
                return False

        return True

    def maybe_capture(self, img, tag: str = "attack", source: str = "unknown", meta: dict = None) -> bool:
        if img is None or not self._should_capture(source):
            return False

        data, ext = self._encode(img)
        if not data:
            return False

        digest = hashlib.md5(data).hexdigest()
        with self._lock:
            if digest in self._hashes:
                return False
            if len(self._hashes) > 1000:
                self._hashes.clear()
            self._hashes.add(digest)
            self._count += 1
            self._last_time = time.time()
            index = self._count

        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]
        safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in (tag or "attack"))
        path = os.path.join(self.out_dir, f"auto_{stamp}_{safe_tag}_{index:05d}{ext}")

        meta = dict(meta or {})
        meta.update({
            "tag": tag,
            "source": source,
            "timestamp": stamp,
            "index": index,
            "format": ext.lstrip("."),
            "quality": (self.jpeg_quality if ext == ".jpg"
                        else self.webp_quality if ext == ".webp" else None),
            "size_bytes": len(data),
            "resolution": [int(img.shape[1]), int(img.shape[0])] if hasattr(img, "shape") else None,
            "mean_brightness": float(img.mean()) if hasattr(img, "mean") else None,
        })

        try:
            self._queue.put_nowait((path, data, meta))
        except queue.Full:
            # Attack must not block on disk I/O; drop the frame.
            with self._lock:
                self._count -= 1
            return False

        if self._count % 25 == 0:
            print(f"[CAPTURE] saved={self._count} latest={os.path.basename(path)}")
        return True


_CAPTURE = None
_CAPTURE_KEY = None


def get_capture(cfg: dict = None) -> DatasetCapture:
    """Singleton capture configured from settings.json."""
    global _CAPTURE, _CAPTURE_KEY

    cfg = cfg or {}
    key = (
        bool(cfg.get("auto_capture_dataset", False)),
        str(cfg.get("auto_capture_dir", "")),
        float(cfg.get("auto_capture_min_interval_sec", 2.0)),
        int(cfg.get("auto_capture_max_files", 2000)),
        bool(cfg.get("auto_capture_only_on_fallback", True)),
        float(cfg.get("auto_capture_success_sample", 0.1)),
        float(cfg.get("auto_capture_scout_sample", 1.0)),
        bool(cfg.get("auto_capture_on_scout", True)),
        bool(cfg.get("auto_capture_on_attack", True)),
        _normalize_format(cfg.get("auto_capture_format", "jpg")),
        int(cfg.get("auto_capture_jpeg_quality", 92)),
        int(cfg.get("auto_capture_webp_quality", 90)),
        int(cfg.get("auto_capture_png_compression", 9)),
    )

    if _CAPTURE is None or _CAPTURE_KEY != key:
        _CAPTURE = DatasetCapture(
            enabled=key[0],
            out_dir=key[1],
            min_interval_sec=key[2],
            max_files=key[3],
            only_on_fallback=key[4],
            success_sample=key[5],
            scout_sample=key[6],
            capture_on_scout=key[7],
            capture_on_attack=key[8],
            image_format=key[9],
            jpeg_quality=key[10],
            webp_quality=key[11],
            png_compression=key[12],
        )
        _CAPTURE_KEY = key

    return _CAPTURE
