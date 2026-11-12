"""Home-village resource and builder readouts for the shell.

Coordinates are calibrated for the 860x732 MEmu frame used everywhere else in
the project: the four currency counters sit in the top-right corner and the
builder/lab counters sit just above the Build button.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Mapping

import cv2
import numpy as np

from COCbot.core.ports import CapturePort, LoggerPort
from COCbot.core.vision.image import frame_image
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point, Rect

HOME_GOLD_REGION = Rect(639, 14, 216, 33)
HOME_ELIXIR_REGION = Rect(641, 49, 210, 35)
HOME_DARK_REGION = Rect(693, 87, 160, 35)
HOME_GEMS_REGION = Rect(692, 123, 160, 37)
# "5/5" builders and "1/2" researchers, above the Build button.
HOME_BUILDERS_REGION = Rect(740, 596, 64, 40)
# Whole currency column, read in one GLM-OCR request.
HOME_TOP_BAR_REGION = Rect(639, 14, 216, 146)

GLM_NUMBER_PROMPT = (
    "Read every number in this image from top to bottom, one number per line. "
    "Digits only, no explanation."
)
GLM_TEXT_PROMPT = "Read the text exactly, characters only, no explanation."

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


def regions_from_config(mapping: object) -> dict[str, Rect]:
    """Convert ``{key: [x, y, w, h]}`` from settings into ``Rect`` values."""
    allowed = ("gold", "elixir", "dark", "gems", "builders")
    result: dict[str, Rect] = {}
    if not isinstance(mapping, dict):
        return result
    for key in allowed:
        value = mapping.get(key)
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            continue
        try:
            x, y, width, height = (int(part) for part in value)
        except (TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            result[key] = Rect(x, y, width, height)
    return result


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


@dataclass(frozen=True)
class ResourceCapacity:
    """Capacity tooltip of one resource (read after tapping its bar)."""

    resource: str
    maximum: int | None = None
    production: int | None = None
    treasury: int | None = None


# Bar centres and the tooltip band that opens right below each bar.
CAPACITY_TAPS: dict[str, Point] = {
    "gold": Point(760, 30),
    "elixir": Point(760, 66),
    "dark": Point(760, 104),
}
CAPACITY_TOOLTIP_X = 620
CAPACITY_TOOLTIP_WIDTH = 240
CAPACITY_TOOLTIP_HEIGHT = 84


def _parse_amount(text: str) -> int | None:
    """Parse ``7,950,000`` or ``0.49M`` into an integer."""
    import re

    cleaned = text.replace(" ", "").replace(",", "").replace("'", "")
    match = re.search(r"(\d+(?:\.\d+)?)([KM]?)", cleaned)
    if match is None:
        return None
    value = float(match.group(1))
    suffix = match.group(2).upper()
    if suffix == "M":
        value *= 1_000_000
    elif suffix == "K":
        value *= 1_000
    return int(round(value))


class ResourceReader:
    """Capture the home village and read its counters."""

    def __init__(
        self,
        capture: CapturePort,
        logger: LoggerPort | None = None,
        number_reader: Callable[[np.ndarray], int | None] | None = None,
        fraction_reader: Callable[[np.ndarray], tuple[int, int] | None] | None = None,
        glm_server: str | None = None,
        glm_client: Callable[[np.ndarray, str], str] | None = None,
        regions: Mapping[str, Rect] | None = None,
        adb: object | None = None,
    ) -> None:
        """Create the reader with optional injected OCR callables."""
        self._capture = capture
        self._logger = logger
        self._read_number = number_reader or ocr_number
        self._read_fraction = fraction_reader or ocr_fraction
        self._glm_server = glm_server or None
        self._glm_client = glm_client
        self._glm_ok: bool | None = None
        self._glm_checked_at = 0.0
        overrides = dict(regions or {})
        self._adb = adb
        self._regions = {
            "gold": overrides.get("gold", HOME_GOLD_REGION),
            "elixir": overrides.get("elixir", HOME_ELIXIR_REGION),
            "dark": overrides.get("dark", HOME_DARK_REGION),
            "gems": overrides.get("gems", HOME_GEMS_REGION),
            "builders": overrides.get("builders", HOME_BUILDERS_REGION),
        }
        self._top_region = self._bounding_region(
            self._regions["gold"],
            self._regions["elixir"],
            self._regions["dark"],
            self._regions["gems"],
        )

    @staticmethod
    def _bounding_region(*regions: Rect) -> Rect:
        """Return the rectangle that covers every region."""
        left = min(region.x for region in regions)
        top = min(region.y for region in regions)
        right = max(region.right for region in regions)
        bottom = max(region.bottom for region in regions)
        return Rect(left, top, right - left, bottom - top)

    def _glm_ready(self) -> bool:
        """Return ``True`` when a local GLM-OCR server answers."""
        if self._glm_client is not None:
            return True
        if not self._glm_server:
            return False
        now = time.time()
        if self._glm_ok is not None:
            if self._glm_ok:
                return True
            if now - self._glm_checked_at < 60.0:
                return False
        import urllib.request

        try:
            with urllib.request.urlopen(
                self._glm_server.rstrip("/") + "/health", timeout=2
            ) as response:
                self._glm_ok = response.status == 200
        except Exception:
            self._glm_ok = False
        self._glm_checked_at = now
        if self._glm_ok:
            self._log("info", f"GLM-OCR readout active at {self._glm_server}")
        return bool(self._glm_ok)

    def _ask_glm(self, image: np.ndarray, prompt: str) -> str:
        """Send one crop to GLM-OCR (local llama.cpp server)."""
        if self._glm_client is not None:
            return self._glm_client(image, prompt)
        import base64
        import json
        import urllib.request

        ok, buffer = cv2.imencode(".png", image)
        if not ok:
            return ""
        payload = {
            "model": "glm-ocr",
            "temperature": 0,
            "max_tokens": 96,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,"
                                + base64.b64encode(buffer.tobytes()).decode("ascii")
                            },
                        },
                    ],
                }
            ],
        }
        request = urllib.request.Request(
            (self._glm_server or "").rstrip("/") + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self._log("warning", f"GLM-OCR request failed: {exc}")
            self._glm_ok = False
            return ""
        choices = body.get("choices") or []
        if not choices:
            return ""
        return str(choices[0].get("message", {}).get("content", ""))

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
        crop = self._crop(frame, self._regions["builders"])
        if crop is None:
            return (None, None)
        result = self._read_fraction(crop)
        if result is None:
            return (None, None)
        available, total = result
        if total <= 0 or total > MAX_BUILDERS or available > total:
            return (None, None)
        return (available, total)

    def _read_with_glm(self, frame: Frame) -> VillageResources | None:
        """Read all counters with one GLM-OCR request, or ``None``."""
        top = self._crop(frame, self._top_region)
        builders_crop = self._crop(frame, self._regions["builders"])
        if top is None:
            return None
        text = self._ask_glm(top, GLM_NUMBER_PROMPT)
        numbers: list[int] = []
        for line in str(text).splitlines():
            digits = "".join(ch for ch in line if ch.isdigit())
            if digits:
                numbers.append(int(digits))
        if len(numbers) < 4:
            return None
        gold, elixir, dark, gems = numbers[:4]
        for value, limit in (
            (gold, MAX_RESOURCE),
            (elixir, MAX_RESOURCE),
            (dark, MAX_RESOURCE),
            (gems, MAX_GEMS),
        ):
            if value > limit:
                return None
        available = total = None
        if builders_crop is not None:
            builder_text = self._ask_glm(builders_crop, GLM_TEXT_PROMPT)
            digits = [ch for ch in str(builder_text) if ch.isdigit() or ch == "/"]
            joined = "".join(digits)
            if "/" in joined:
                left, right = joined.split("/", 1)
                if left.isdigit() and right.isdigit():
                    a, b = int(left), int(right)
                    if 0 <= a <= b <= MAX_BUILDERS:
                        available, total = a, b
        return VillageResources(
            gold=gold,
            elixir=elixir,
            dark_elixir=dark,
            gems=gems,
            builders_available=available,
            builders_total=total,
        )

    def read_capacity(self, resource: str = "gold") -> ResourceCapacity | None:
        """Tap a resource bar, read its capacity tooltip, then close it."""
        tap = CAPACITY_TAPS.get(resource)
        if tap is None or self._adb is None or not self._glm_ready():
            return None
        region = self._regions.get(resource, HOME_GOLD_REGION)
        tooltip = Rect(
            CAPACITY_TOOLTIP_X,
            region.bottom + 2,
            CAPACITY_TOOLTIP_WIDTH,
            CAPACITY_TOOLTIP_HEIGHT,
        )
        tap_method = getattr(self._adb, "tap", None)
        if tap_method is None:
            return None
        tap_method(tap.x, tap.y)
        time.sleep(1.0)
        frame = self._capture.capture()
        result = None
        if frame is not None:
            crop = self._crop(frame, tooltip)
            if crop is not None:
                text = self._ask_glm(
                    crop,
                    "Read all text exactly as it appears, one line per line. "
                    "No explanation.",
                )
                if text:
                    maximum = production = treasury = None
                    for line in str(text).splitlines():
                        lowered = line.lower()
                        if "max" in lowered:
                            maximum = _parse_amount(
                                line[lowered.index("max") + 3 :]
                            )
                        elif "production" in lowered:
                            tail = line[lowered.index("production") + 10 :]
                            if "hour" in tail.lower():
                                tail = tail[tail.lower().index("hour") + 4 :]
                            production = _parse_amount(tail)
                        elif "treasury" in lowered:
                            treasury = _parse_amount(
                                line[lowered.index("treasury") + 8 :]
                            )
                    result = ResourceCapacity(
                        resource,
                        maximum=maximum,
                        production=production,
                        treasury=treasury,
                    )
        tap_method(tap.x, tap.y)
        time.sleep(0.5)
        return result

    def read(self) -> VillageResources:
        """Return one snapshot; unreadable counters stay ``None``."""
        frame = self._capture.capture()
        if frame is None:
            return VillageResources()
        if self._glm_ready():
            try:
                snapshot = self._read_with_glm(frame)
            except Exception as exc:
                self._log("warning", f"GLM-OCR read failed: {exc}")
                snapshot = None
            if snapshot is not None and snapshot.has_values():
                return snapshot
        builders_available, builders_total = self._builders(frame)
        snapshot = VillageResources(
            gold=self._number(frame, self._regions["gold"], MAX_RESOURCE),
            elixir=self._number(frame, self._regions["elixir"], MAX_RESOURCE),
            dark_elixir=self._number(frame, self._regions["dark"], MAX_RESOURCE),
            gems=self._number(frame, self._regions["gems"], MAX_GEMS),
            builders_available=builders_available,
            builders_total=builders_total,
        )
        if not snapshot.has_values():
            self._log("debug", "Resource readout found no counters on screen")
        return snapshot
