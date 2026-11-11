"""Hero/defense upgrade flow with template + OCR validation.

The upgrade entry point in the current game build is the *Buildings & Heroes*
panel: it lists every suggested/other upgrade, tapping a row opens the
``Upgrade <target> to Level N?`` dialog, and only the green ``CONFIRM`` button
spends resources.

That makes a blind tap unacceptable, so the flow validates every step:

1. open the panel through the fixed quick-access shortcut;
2. read the row names with OCR and match the requested hero/building;
3. after tapping a row, require the dialog title to mention the target;
4. require the ``confirm_button.png`` template before tapping;
5. dismiss the dialog with ``close_button.png`` when it is still visible.

Templates live in ``Templates/upgrade``:

``hero/*.png``            one portrait per hero (identification helpers)
``upgrade_button.png``    map info-panel Upgrade button
``confirm_button.png``    green CONFIRM button of the upgrade dialog
``close_button.png``      red X of the upgrade dialog

Dry-run is the default; ``execute=True`` is required to spend resources.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

import cv2
import numpy as np

from COCbot.core.config.paths import get_project_paths
from COCbot.core.ports import AdbPort, CapturePort, ClockPort, LoggerPort
from COCbot.core.vision.image import frame_image, imread
from COCbot.models.frame import Frame
from COCbot.models.geometry import Point, Rect

# Home-village quick access that opens the "Buildings & Heroes" panel.
PANEL_SHORTCUT = Point(752, 603)
# Panel list area (right side of the 860x732 frame) and its title.
PANEL_REGION = Rect(492, 40, 368, 660)
# Name column only: icons on the left and cost/time on the right are excluded.
PANEL_NAME_REGION = Rect(545, 40, 190, 660)
PANEL_TITLE_REGION = Rect(560, 8, 250, 40)
PANEL_TAP_X = 620
PANEL_ROW_OFFSET = 12
# Upgrade dialog title and the region used for the confirm/close templates.
DIALOG_TITLE_REGION = Rect(190, 105, 500, 42)
DIALOG_REGION = Rect(0, 80, 860, 600)
DIALOG_CLOSE_REGION = Rect(780, 105, 70, 55)
PANEL_CLOSE_REGION = Rect(795, 6, 55, 45)

PANEL_TITLE_KEYWORDS = ("buildings", "heroes")
FUZZY_ROW_THRESHOLD = 0.80
ROW_SKIP_KEYWORDS = (
    "suggested",
    "other upgrades",
    "upgrade",
    "gold pass",
    "stronger",
    "turn spells",
    "hitpoints",
    "damage",
    "duration",
    "level",
)
ROW_HEADERS = ("suggested upgrades", "other upgrades")


@dataclass(frozen=True)
class UpgradeTarget:
    """One hero or defense candidate."""

    name: str
    kind: str
    template: str


@dataclass(frozen=True)
class UpgradeRow:
    """One row of the Buildings & Heroes list."""

    name: str
    point: Point


DEFAULT_TARGETS: tuple[UpgradeTarget, ...] = (
    UpgradeTarget("Barbarian King", "hero", "hero/barbarian_king.png"),
    UpgradeTarget("Archer Queen", "hero", "hero/archer_queen.png"),
    UpgradeTarget("Grand Warden", "hero", "hero/grand_warden.png"),
    UpgradeTarget("Royal Champion", "hero", "hero/royal_champion.png"),
    UpgradeTarget("Dragon Duke", "hero", "hero/dragon_duke.png"),
    UpgradeTarget("Minion Prince", "hero", "hero/minion_prince.png"),
)

DEFAULT_BUTTONS: Mapping[str, str] = {
    "upgrade": "upgrade_button.png",
    "confirm": "confirm_button.png",
    "close": "close_button.png",
}


@dataclass(frozen=True)
class UpgradeResult:
    """Outcome of a hero/defense upgrade attempt."""

    ok: bool
    target: str = ""
    executed: bool = False
    message: str = ""
    taps: int = 0


def _normalize(text: str) -> str:
    """Return lowercase alphanumerics only, for lenient name matching."""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _ocr_text(frame_or_image: Frame | np.ndarray, region: Rect) -> str:
    """Return lowercase OCR text from *region* (empty when unavailable)."""
    try:
        import pytesseract
    except Exception:
        return ""
    image = frame_image(frame_or_image)
    if image is None:
        return ""
    crop = image[region.y : region.bottom, region.x : region.right]
    if crop.size == 0:
        return ""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    try:
        return pytesseract.image_to_string(gray, config="--psm 6").lower()
    except Exception:
        return ""


def _ocr_lines(frame: Frame, threshold: int) -> list[tuple[int, str]]:
    """Return ``(y, name)`` lines from the panel name column at one threshold."""
    try:
        import pytesseract
    except Exception:
        return []
    image = frame_image(frame)
    if image is None:
        return []
    region = PANEL_NAME_REGION
    crop = image[region.y : region.bottom, region.x : region.right]
    if crop.size == 0:
        return []
    # Keep the white row names plus the green "new" labels, and drop the icon
    # column on the left and the cost/time column on the right.
    if crop.ndim == 3:
        blue = crop[:, :, 0].astype(int)
        green = crop[:, :, 1].astype(int)
        red = crop[:, :, 2].astype(int)
        white = (red > threshold) & (green > threshold) & (blue > threshold)
        accent = (green > threshold) & (green > red + 25) & (green > blue + 25)
        mask = (white | accent).astype(np.uint8) * 255
    else:
        mask = crop
    scale = 3
    big = cv2.resize(mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    try:
        data = pytesseract.image_to_data(
            big,
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )
    except Exception:
        return []

    lines: dict[tuple[int, int, int], list[tuple[float, float, str]]] = {}
    texts = data.get("text", [])
    for index, raw in enumerate(texts):
        word = str(raw).strip()
        if len(word) < 3 or not any(ch.isalpha() for ch in word):
            continue
        key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        left = float(data["left"][index]) / scale + region.x
        top = float(data["top"][index]) / scale + region.y
        height = float(data["height"][index]) / scale
        lines.setdefault(key, []).append((left, top + height / 2, word))

    results: list[tuple[int, str]] = []
    for words in lines.values():
        words.sort(key=lambda item: item[0])
        name = " ".join(word for _, _, word in words).strip()
        lowered = _normalize(name)
        raw_lower = name.lower()
        if not name or len(lowered) < 4:
            continue
        if any(flag in raw_lower for flag in ROW_SKIP_KEYWORDS):
            continue
        if any(
            difflib.SequenceMatcher(None, lowered, _normalize(header)).ratio() >= 0.8
            for header in ROW_HEADERS
        ):
            continue
        center_y = int(sum(y for _, y, _ in words) / len(words))
        results.append((center_y, name))
    return results


def _ocr_rows(frame: Frame) -> list[UpgradeRow]:
    """Return the upgrade rows visible in the Buildings & Heroes panel.

    Two thresholds are merged because the panel mixes pure white names with
    green/gold labels: one pass reads the white text, the other rescues the
    tinted rows (``Gold Mine x 7``) that the first pass loses.
    """
    from COCbot.features.village.targets import canonical_name

    merged: list[list] = []  # [y, name]
    for threshold in (130, 145):
        for y, name in _ocr_lines(frame, threshold):
            match = None
            for entry in merged:
                if abs(entry[0] - y) <= 12:
                    match = entry
                    break
            if match is None:
                merged.append([y, name])
                continue
            if canonical_name(match[1]) is None and canonical_name(name) is not None:
                match[1] = name
            elif len(name) > len(match[1]) and canonical_name(match[1]) is None:
                match[1] = name

    rows = [
        UpgradeRow(name=name, point=Point(PANEL_TAP_X, y + PANEL_ROW_OFFSET))
        for y, name in merged
    ]
    rows.sort(key=lambda row: row.point.y)
    return rows


class HeroDefenseUpgrader:
    """Find an upgrade row and execute a fully validated upgrade."""

    def __init__(
        self,
        adb: AdbPort,
        capture: CapturePort,
        clock: ClockPort | None = None,
        logger: LoggerPort | None = None,
        template_dir: Path | str | None = None,
        targets: Sequence[UpgradeTarget] = DEFAULT_TARGETS,
        buttons: Mapping[str, str] = DEFAULT_BUTTONS,
        threshold: float = 0.75,
        execute: bool = False,
        rows_provider: Callable[[Frame], Sequence[UpgradeRow]] | None = None,
        text_reader: Callable[[Frame, Rect], str] | None = None,
        label_dir: Path | str | None = None,
    ) -> None:
        """Create the upgrader; missing templates simply disable buttons."""
        from COCbot.core.clock import SystemClock

        self._adb = adb
        self._capture = capture
        self._clock = clock or SystemClock()
        self._logger = logger
        self._dir = (
            Path(template_dir)
            if template_dir is not None
            else get_project_paths().templates_dir / "upgrade"
        )
        paths = get_project_paths()
        self._label_dir = (
            Path(label_dir) if label_dir is not None else paths.templates_dir / "buildings"
        )
        self._targets = tuple(targets)
        self._buttons = dict(buttons)
        self._threshold = threshold
        self._execute = execute
        self._rows_provider = rows_provider or _ocr_rows
        self._text_reader = text_reader or _ocr_text

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _load(self, filename: str) -> np.ndarray | None:
        """Load one template from the upgrade template directory."""
        path = self._dir / filename
        return imread(path) if path.is_file() else None

    def available_targets(self) -> list[str]:
        """Return targets whose portrait template exists."""
        return [target.name for target in self._targets if (self._dir / target.template).is_file()]

    @staticmethod
    def _match(image: np.ndarray, template: np.ndarray, threshold: float) -> Point | None:
        """Return the best match center above *threshold*."""
        if (
            template.shape[0] > image.shape[0]
            or template.shape[1] > image.shape[1]
        ):
            return None
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(result)
        if not np.isfinite(score) or score < threshold:
            return None
        return Point(
            location[0] + template.shape[1] // 2,
            location[1] + template.shape[0] // 2,
        )

    def find(self, frame: Frame, template_name: str, region: Rect | None = None) -> Point | None:
        """Find a template in *frame*, optionally limited to *region*."""
        image = frame_image(frame)
        template = self._load(template_name)
        if image is None or template is None:
            return None
        if region is None:
            return self._match(image, template, self._threshold)
        crop = image[region.y : region.bottom, region.x : region.right]
        if crop.size == 0:
            return None
        point = self._match(crop, template, self._threshold)
        if point is None:
            return None
        return Point(point.x + region.x, point.y + region.y)

    def rows(self, frame: Frame) -> list[UpgradeRow]:
        """Return the upgrade rows visible in *frame*.

        OCR rows are merged with template labels from ``Templates/buildings``
        (``grandwarden.png``, ``minionprince.png``, ``wall.png`` …), which are
        pixel-exact and rescue rows the OCR pass mangles.
        """
        rows = list(self._rows_provider(frame))
        for name, point in self._label_rows(frame):
            match = None
            for row in rows:
                if abs(row.point.y - point.y) <= 14:
                    match = row
                    break
            if match is None:
                rows.append(UpgradeRow(name, point))
            elif _normalize(match.name) != _normalize(name):
                index = rows.index(match)
                rows[index] = UpgradeRow(name, point)
        rows.sort(key=lambda row: row.point.y)
        return rows

    def _label_rows(self, frame: Frame) -> list[tuple[str, Point]]:
        """Return ``(name, point)`` for every label template found in the panel."""
        from COCbot.features.village.targets import canonical_name

        image = frame_image(frame)
        if image is None or not self._label_dir.is_dir():
            return []
        region = PANEL_NAME_REGION
        crop = image[region.y : region.bottom, region.x : region.right]
        if crop.size == 0:
            return []
        found: list[tuple[str, Point]] = []
        for path in sorted(self._label_dir.glob("*.png")):
            stem = path.stem
            if stem.lower() == "buildings&heroes":
                continue
            template = imread(path)
            if template is None:
                continue
            point = self._match(crop, template, max(0.80, self._threshold))
            if point is None:
                continue
            name = canonical_name(stem) or stem.replace("_", " ").title()
            found.append(
                (
                    name,
                    Point(PANEL_TAP_X, point.y + region.y),
                )
            )
        return found

    def scan_rows(self, execute: bool = True) -> list[UpgradeRow]:
        """Open the panel, read every row, then close it again."""
        if not self.open_panel(execute=execute):
            return []
        frame = self._capture.capture()
        rows = self.rows(frame) if frame is not None else []
        if execute:
            self.dismiss(execute=True)
        return rows

    def find_row(self, rows: Sequence[UpgradeRow], name: str) -> UpgradeRow | None:
        """Return the row whose OCR text matches *name*.

        Exact substrings win; OCR slips such as ``Here Hall`` for
        ``Hero Hall`` still match through a fuzzy fallback.
        """
        wanted = _normalize(name)
        if not wanted:
            return None
        for row in rows:
            if wanted in _normalize(row.name):
                return row
        best_row = None
        best_score = 0.0
        for row in rows:
            score = difflib.SequenceMatcher(None, wanted, _normalize(row.name)).ratio()
            if score > best_score:
                best_row, best_score = row, score
        if best_row is not None and best_score >= FUZZY_ROW_THRESHOLD:
            return best_row
        return None

    def panel_open(self, frame: Frame) -> bool:
        """Return ``True`` when the Buildings & Heroes panel is visible."""
        title_path = self._label_dir / "Buildings&Heroes.png"
        if title_path.is_file():
            image = frame_image(frame)
            template = imread(title_path)
            if image is not None and template is not None:
                point = self._match(image, template, max(0.80, self._threshold))
                if point is not None:
                    return True
        title = self._text_reader(frame, PANEL_TITLE_REGION)
        return any(keyword in title for keyword in PANEL_TITLE_KEYWORDS)

    def dialog_open(self, frame: Frame) -> bool:
        """Return ``True`` when the upgrade confirm dialog is on screen."""
        return self.find(frame, self._buttons["confirm"], DIALOG_REGION) is not None

    def dismiss(self, execute: bool = True) -> bool:
        """Close the upgrade dialog or the panel, never confirming anything."""
        frame = self._capture.capture()
        if frame is None:
            return False
        if self.dialog_open(frame):
            target = self.find(frame, self._buttons["close"], DIALOG_CLOSE_REGION)
        else:
            target = self.find(frame, self._buttons["close"], PANEL_CLOSE_REGION)
        if target is None:
            return False
        if not execute:
            self._log("info", "Dry run: would close the upgrade window")
            return False
        self._adb.tap(target.x, target.y)
        self._clock.sleep(0.7)
        return True

    def close_panel(self, execute: bool = True) -> bool:
        """Alias for :meth:`dismiss`."""
        return self.dismiss(execute=execute)

    def open_panel(self, execute: bool = True) -> bool:
        """Open the Buildings & Heroes panel when it is not already visible."""
        frame = self._capture.capture()
        if frame is None:
            return False
        if self.dialog_open(frame):
            if not execute:
                self._log("info", "Dry run: would close the upgrade dialog first")
                return False
            self.dismiss(execute=True)
            frame = self._capture.capture()
            if frame is None:
                return False
        if self.panel_open(frame):
            return True
        if not execute:
            self._log("info", "Dry run: would open the Buildings & Heroes panel")
            return False
        self._adb.tap(PANEL_SHORTCUT.x, PANEL_SHORTCUT.y)
        self._clock.sleep(1.5)
        frame = self._capture.capture()
        return bool(frame is not None and self.panel_open(frame))

    def execute(self, target_name: str | None = None, execute: bool | None = None) -> UpgradeResult:
        """Run one upgrade flow; dry-run returns the plan only."""
        should_tap = self._execute if execute is None else bool(execute)
        frame = self._capture.capture()
        if frame is None:
            return UpgradeResult(False, message="Capture failed")

        if self.dialog_open(frame):
            self.dismiss(execute=True)
            frame = self._capture.capture()
            if frame is None:
                return UpgradeResult(False, message="Capture failed")

        if not self.panel_open(frame):
            if not should_tap:
                return UpgradeResult(
                    True,
                    target_name or "",
                    executed=False,
                    message="Dry run: would open the Buildings & Heroes panel",
                )
            if not self.open_panel(execute=True):
                return UpgradeResult(
                    False,
                    target_name or "",
                    message="Buildings & Heroes panel did not open",
                )
            frame = self._capture.capture()
            if frame is None:
                return UpgradeResult(False, target_name or "", message="Capture failed")

        rows = self.rows(frame)
        if not rows:
            return UpgradeResult(
                False,
                target_name or "",
                message="Upgrade panel rows not readable",
            )

        row: UpgradeRow | None = None
        name = (target_name or "").strip()
        if name:
            row = self.find_row(rows, name)
            if row is None:
                listed = ", ".join(item.name for item in rows)
                return UpgradeResult(
                    False,
                    name,
                    message=f"{name} not listed in the upgrade panel (rows: {listed})",
                )
        else:
            for target in self._targets:
                row = self.find_row(rows, target.name)
                if row is not None:
                    name = target.name
                    break
            if row is None:
                return UpgradeResult(
                    False,
                    message="No configured hero/defense row found",
                )

        if not should_tap:
            return UpgradeResult(
                True,
                name,
                executed=False,
                message=f"Dry run: would open {name} at ({row.point.x},{row.point.y})",
            )

        taps = 0
        self._adb.tap(row.point.x, row.point.y)
        taps += 1
        self._clock.sleep(1.2)

        frame = self._capture.capture()
        if frame is None:
            return UpgradeResult(False, name, taps=taps, message="Capture failed")
        title = self._text_reader(frame, DIALOG_TITLE_REGION)
        if _normalize(name) not in _normalize(title):
            return UpgradeResult(
                False,
                name,
                taps=taps,
                message=f"Upgrade dialog does not mention {name}: {title.strip()!r}",
            )

        confirm = self.find(frame, self._buttons["confirm"], DIALOG_REGION)
        if confirm is None:
            return UpgradeResult(
                False,
                name,
                taps=taps,
                message="Confirm button template not found",
            )
        self._adb.tap(confirm.x, confirm.y)
        taps += 1
        self._clock.sleep(0.8)

        frame = self._capture.capture()
        close = (
            self.find(frame, self._buttons["close"], DIALOG_CLOSE_REGION)
            if frame is not None
            else None
        )
        if close is not None:
            self._adb.tap(close.x, close.y)
            taps += 1
        return UpgradeResult(
            True,
            name,
            executed=True,
            taps=taps,
            message=f"Upgraded {name}",
        )
