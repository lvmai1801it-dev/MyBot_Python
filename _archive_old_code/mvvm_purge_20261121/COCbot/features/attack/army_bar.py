"""Army-bar scanning: detect troops, heroes, spells, and siege slots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cv2
import numpy as np

from COCbot.core.config.coordinates import (
    ARMY_BADGE_HEIGHT,
    ARMY_BAR_Y,
    ARMY_CARD_HEIGHT,
    ARMY_CARD_WIDTH,
    ARMY_SLOT_START_X,
    ARMY_SLOT_STEP,
)
from COCbot.core.config.paths import get_project_paths
from COCbot.core.ports import LoggerPort, OcrPort
from COCbot.core.vision.image import crop, frame_image
from COCbot.models.frame import Frame
from COCbot.models.geometry import Rect


class ArmySlotKind(str, Enum):
    """Category of one attack-bar card."""

    TROOP = "troop"
    SPELL = "spell"
    HERO = "hero"
    SIEGE = "siege"


@dataclass(frozen=True)
class ArmySlot:
    """One detected attack-bar card."""

    name: str
    slot: int
    count: int
    kind: ArmySlotKind

    def tap_point(self) -> tuple[int, int]:
        """Return the card center used to select this slot."""
        return (
            ARMY_SLOT_START_X + self.slot * ARMY_SLOT_STEP + ARMY_CARD_WIDTH // 2,
            ARMY_BAR_Y + ARMY_CARD_HEIGHT // 2,
        )


def normalize_template(image: np.ndarray) -> np.ndarray:
    """Crop oversized card art and scale it to the 42x42 slot template size."""
    height, width = image.shape[:2]
    if height > 55 or width > 55:
        crop_img = image[int(height * 0.18) : int(height * 0.80), int(width * 0.18) : int(width * 0.82)]
        return cv2.resize(crop_img, (42, 42), interpolation=cv2.INTER_AREA)
    return image


class ArmyBarScanner:
    """Detect the cards currently available in the attack bar."""

    HERO_FILES = {
        "King": "bk.png",
        "Queen": "queen.png",
        "Warden": "warden.png",
        "Champion": "rc.png",
        "Prince": "prince.png",
    }

    def __init__(
        self,
        templates_dir: Path | str | None = None,
        ocr: OcrPort | None = None,
        logger: LoggerPort | None = None,
        hero_threshold: float = 0.55,
        siege_threshold: float = 0.58,
        troop_threshold: float = 0.55,
        spell_threshold: float = 0.55,
        empty_threshold: float = 0.70,
    ) -> None:
        """Load and normalize every card template once."""
        self._dir = Path(templates_dir) if templates_dir else get_project_paths().templates_dir
        self._ocr = ocr
        self._logger = logger
        self._hero_threshold = hero_threshold
        self._siege_threshold = siege_threshold
        self._troop_threshold = troop_threshold
        self._spell_threshold = spell_threshold
        self._empty_threshold = empty_threshold
        self._templates = self._load_templates()

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def _load_dir(self, directory: Path) -> dict[str, np.ndarray]:
        """Load every PNG in *directory* as a normalized BGR template."""
        result: dict[str, np.ndarray] = {}
        if not directory.is_dir():
            return result
        for path in sorted(directory.glob("*.png")):
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is not None:
                result[path.stem] = normalize_template(image)
        return result

    def _load_templates(self) -> dict[ArmySlotKind, dict[str, np.ndarray]]:
        """Load troop, spell, siege, and hero templates."""
        smart = self._dir / "Smart_Auto_train"
        heroes: dict[str, np.ndarray] = {}
        for name, filename in self.HERO_FILES.items():
            path = self._dir / filename
            if path.is_file():
                image = cv2.imread(str(path), cv2.IMREAD_COLOR)
                if image is not None:
                    heroes[name] = normalize_template(image)
        return {
            ArmySlotKind.TROOP: self._load_dir(smart / "Army Troops"),
            ArmySlotKind.SPELL: self._load_dir(smart / "Spells"),
            ArmySlotKind.SIEGE: self._load_dir(smart / "Siege Machines"),
            ArmySlotKind.HERO: heroes,
        }

    @staticmethod
    def _score(slot_image: np.ndarray, template: np.ndarray) -> float:
        """Return the best template-match score inside a slot."""
        if (
            template.shape[0] > slot_image.shape[0]
            or template.shape[1] > slot_image.shape[1]
        ):
            return 0.0
        result = cv2.matchTemplate(slot_image, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, _ = cv2.minMaxLoc(result)
        return float(score) if np.isfinite(score) else 0.0

    def _best(
        self,
        slot_image: np.ndarray,
        templates: dict[str, np.ndarray],
    ) -> tuple[str, float]:
        """Return the highest-scoring template name and score."""
        best_name = ""
        best_score = 0.0
        for name, template in templates.items():
            score = self._score(slot_image, template)
            if score > best_score:
                best_name, best_score = name, score
        return best_name, best_score

    def _badge_present(self, image: np.ndarray, slot_x: int) -> bool:
        """Return ``True`` when the card shows a troop-count badge."""
        badge = crop(
            image,
            Rect(
                slot_x + 8,
                ARMY_BAR_Y,
                54,
                ARMY_BADGE_HEIGHT,
            ),
        )
        if badge.size == 0:
            return False
        mean_b, _mean_g, mean_r = cv2.mean(badge)[:3]
        return mean_b >= 85 and mean_b > mean_r + 15

    def _read_count(self, frame: Frame, slot_x: int, has_badge: bool) -> int:
        """Read the troop count from the badge, falling back to a sane value."""
        if self._ocr is not None:
            value = self._ocr.read_number(
                frame,
                Rect(slot_x + 8, ARMY_BAR_Y, 54, ARMY_BADGE_HEIGHT),
            )
            if value and value > 0:
                return int(value)
        return 10 if has_badge else 1

    def scan(self, frame: Frame) -> list[ArmySlot]:
        """Return every non-empty attack-bar slot."""
        image = frame_image(frame)
        if image is None:
            return []
        height, width = image.shape[:2]
        slots: list[ArmySlot] = []
        for index in range(11):
            slot_x = ARMY_SLOT_START_X + index * ARMY_SLOT_STEP
            if slot_x + ARMY_CARD_WIDTH > width:
                break
            slot_image = image[
                ARMY_BAR_Y : min(height, ARMY_BAR_Y + ARMY_CARD_HEIGHT),
                slot_x : slot_x + ARMY_CARD_WIDTH,
            ]
            if slot_image.size == 0:
                continue

            hero_name, hero_score = self._best(
                slot_image, self._templates[ArmySlotKind.HERO]
            )
            if hero_name and hero_score >= self._hero_threshold:
                slots.append(ArmySlot(hero_name, index, 1, ArmySlotKind.HERO))
                continue

            siege_name, siege_score = self._best(
                slot_image, self._templates[ArmySlotKind.SIEGE]
            )
            if siege_name and siege_score >= self._siege_threshold:
                slots.append(ArmySlot(siege_name, index, 1, ArmySlotKind.SIEGE))
                continue

            troop_name, troop_score = self._best(
                slot_image, self._templates[ArmySlotKind.TROOP]
            )
            spell_name, spell_score = self._best(
                slot_image, self._templates[ArmySlotKind.SPELL]
            )
            if spell_score >= troop_score:
                name, score, kind = spell_name, spell_score, ArmySlotKind.SPELL
                threshold = self._spell_threshold
            else:
                name, score, kind = troop_name, troop_score, ArmySlotKind.TROOP
                threshold = self._troop_threshold

            has_badge = self._badge_present(image, slot_x)
            if not name or (not has_badge and score < self._empty_threshold):
                continue
            if score < threshold and not has_badge:
                continue
            count = self._read_count(frame, slot_x, has_badge)
            slots.append(ArmySlot(name, index, count, kind))
        self._log("info", f"Army bar: {len(slots)} usable slots")
        return slots
