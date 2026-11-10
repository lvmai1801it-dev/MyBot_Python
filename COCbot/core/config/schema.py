"""Typed application settings.

``AppConfig`` is the single in-memory representation of ``settings.json``. It
keeps backward compatibility with the legacy flat JSON file through
``from_legacy_dict`` / ``to_dict`` so old and new code can share the same file
during the migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from COCbot.core.config import defaults
from COCbot.core.config.version import CONFIG_SCHEMA_VERSION
from COCbot.models.enums import AttackSide, EmulatorType


def _as_int(value: Any, default: int) -> int:
    """Convert *value* to int, returning *default* on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    """Convert *value* to float, returning *default* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    """Convert *value* to bool, accepting common string forms."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off", ""):
            return False
    return default


def _as_str(value: Any, default: str) -> str:
    """Convert *value* to a stripped string, returning *default* on failure."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_str_list(value: Any) -> list[str]:
    """Convert *value* to a list of non-empty strings."""
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return *value* when it is a mapping, otherwise an empty mapping."""
    return value if isinstance(value, Mapping) else {}


def _as_count_map(value: Any) -> dict[str, int]:
    """Normalize a ``{name: count}`` mapping, dropping non-positive entries."""
    result: dict[str, int] = {}
    for name, count in _as_mapping(value).items():
        amount = _as_int(count, 0)
        if amount > 0:
            result[str(name)] = amount
    return result


@dataclass(frozen=True)
class ResourceThresholds:
    """Loot thresholds used to decide whether a base is worth attacking."""

    gold: int = 65_000
    elixir: int = 65_000
    dark_elixir: int = 0


@dataclass(frozen=True)
class WallUpgradeConfig:
    """Wall upgrade settings."""

    enabled: bool = False
    level: int = 8
    gold_threshold: int = 5_000_000
    elixir_threshold: int = 5_000_000


@dataclass(frozen=True)
class PriorityUpgradeConfig:
    """Generic enabled/priority list used by non-wall upgrade groups."""

    enabled: bool = False
    priorities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UpgradeConfig:
    """All upgrade groups shown in the village upgrade tab."""

    wall: WallUpgradeConfig = field(default_factory=WallUpgradeConfig)
    hero: PriorityUpgradeConfig = field(default_factory=PriorityUpgradeConfig)
    defense: PriorityUpgradeConfig = field(default_factory=PriorityUpgradeConfig)
    army: PriorityUpgradeConfig = field(default_factory=PriorityUpgradeConfig)
    resource: PriorityUpgradeConfig = field(default_factory=PriorityUpgradeConfig)
    other: PriorityUpgradeConfig = field(default_factory=PriorityUpgradeConfig)


@dataclass(frozen=True)
class RecipeConfig:
    """One army recipe (troops, spells, siege, preferred side)."""

    name: str = "rongdien"
    troops: dict[str, int] = field(default_factory=dict)
    spells: dict[str, int] = field(default_factory=dict)
    siege: dict[str, int] = field(default_factory=dict)
    side: str = "Ngẫu nhiên"

    @property
    def side_enum(self) -> AttackSide:
        """Return the normalized deployment side."""
        return AttackSide.from_value(self.side)


@dataclass(frozen=True)
class AttackConfig:
    """Attack-plan settings."""

    name: str = "Dragon_Attack"
    side: str = "Ngẫu nhiên"
    sides: list[str] = field(default_factory=lambda: ["Ngẫu nhiên"])
    check_troops: bool = False
    recipe: RecipeConfig = field(default_factory=RecipeConfig)

    @property
    def side_enum(self) -> AttackSide:
        """Return the normalized deployment side."""
        return AttackSide.from_value(self.side)


@dataclass(frozen=True)
class TrainingConfig:
    """Army training settings."""

    mode: str = "smart"
    quick_slot: int = 1


@dataclass(frozen=True)
class ClanConfig:
    """Clan Games / Clan Capital / donation settings."""

    enable_clan_games: bool = False
    enable_clan_capital: bool = False
    capital_hall_level: int = 9
    request_troops: bool = True


@dataclass(frozen=True)
class VisionConfig:
    """YOLO and redline detector settings."""

    redline_model: str = defaults.DEFAULT_YOLO_MODEL
    redline_offset_ratio: float = defaults.DEFAULT_REDLINE_OFFSET_RATIO
    confidence: float = defaults.DEFAULT_YOLO_CONFIDENCE
    iou: float = defaults.DEFAULT_YOLO_IOU


@dataclass(frozen=True)
class AutoCaptureConfig:
    """Dataset auto-capture settings."""

    enabled: bool = True
    directory: str = defaults.DEFAULT_AUTO_CAPTURE_DIR
    min_interval_sec: float = defaults.DEFAULT_AUTO_CAPTURE_INTERVAL_SEC
    max_files: int = defaults.DEFAULT_AUTO_CAPTURE_MAX_FILES
    only_on_fallback: bool = True
    success_sample: float = 0.1
    scout_sample: float = 1.0
    on_scout: bool = True
    on_attack: bool = False
    image_format: str = "jpg"
    jpeg_quality: int = defaults.DEFAULT_AUTO_CAPTURE_JPEG_QUALITY
    webp_quality: int = defaults.DEFAULT_AUTO_CAPTURE_WEBP_QUALITY
    png_compression: int = defaults.DEFAULT_AUTO_CAPTURE_PNG_COMPRESSION


@dataclass(frozen=True)
class LoggingConfig:
    """Logging destination and rotation settings."""

    level: str = defaults.DEFAULT_LOG_LEVEL
    file_enabled: bool = True
    file_path: str = defaults.DEFAULT_LOG_FILE
    max_bytes: int = defaults.DEFAULT_LOG_MAX_BYTES
    backup_count: int = defaults.DEFAULT_LOG_BACKUP_COUNT


@dataclass(frozen=True)
class EmulatorConfig:
    """Emulator selection and ADB host."""

    emulator_type: EmulatorType = defaults.DEFAULT_EMULATOR
    host: str = ""
    ld_index: int = 0

    def __post_init__(self) -> None:
        """Normalize the emulator type and fill a default host."""
        normalized = EmulatorType.from_value(self.emulator_type)
        object.__setattr__(self, "emulator_type", normalized)
        if not self.host:
            object.__setattr__(
                self,
                "host",
                defaults.EMULATOR_HOSTS.get(normalized, defaults.EMULATOR_HOSTS[defaults.DEFAULT_EMULATOR]),
            )


@dataclass(frozen=True)
class AppConfig:
    """Complete application configuration."""

    resources: ResourceThresholds = field(default_factory=ResourceThresholds)
    upgrades: UpgradeConfig = field(default_factory=UpgradeConfig)
    attack: AttackConfig = field(default_factory=AttackConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    clan: ClanConfig = field(default_factory=ClanConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    auto_capture: AutoCaptureConfig = field(default_factory=AutoCaptureConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    emulator: EmulatorConfig = field(default_factory=EmulatorConfig)
    enable_stats: bool = False
    schema_version: int = CONFIG_SCHEMA_VERSION

    @classmethod
    def from_legacy_dict(cls, data: Mapping[str, Any]) -> "AppConfig":
        """Build a config from the legacy flat ``settings.json`` mapping."""
        raw = _as_mapping(data)
        recipe = _as_mapping(raw.get("recipe"))

        wall = WallUpgradeConfig(
            enabled=_as_bool(raw.get("upgrade_wall"), False),
            level=_as_int(raw.get("wall_level"), 8),
            gold_threshold=_as_int(raw.get("wall_gold_threshold"), 5_000_000),
            elixir_threshold=_as_int(raw.get("wall_elixir_threshold"), 5_000_000),
        )
        upgrades = UpgradeConfig(
            wall=wall,
            hero=PriorityUpgradeConfig(
                enabled=_as_bool(raw.get("upgrade_hero"), False),
                priorities=_as_str_list(raw.get("hero_priorities")),
            ),
            defense=PriorityUpgradeConfig(
                enabled=_as_bool(raw.get("upgrade_defense"), False),
                priorities=_as_str_list(raw.get("defense_priorities")),
            ),
            army=PriorityUpgradeConfig(
                enabled=_as_bool(raw.get("upgrade_army"), False),
                priorities=_as_str_list(raw.get("army_priorities")),
            ),
            resource=PriorityUpgradeConfig(
                enabled=_as_bool(raw.get("upgrade_resource"), False),
                priorities=_as_str_list(raw.get("resource_priorities")),
            ),
            other=PriorityUpgradeConfig(
                enabled=_as_bool(raw.get("upgrade_other"), False),
                priorities=_as_str_list(raw.get("other_buildings")),
            ),
        )

        recipe_cfg = RecipeConfig(
            name=_as_str(raw.get("recipe_name"), "rongdien"),
            troops=_as_count_map(recipe.get("troops")),
            spells=_as_count_map(recipe.get("spells")),
            siege=_as_count_map(recipe.get("siege")),
            side=_as_str(recipe.get("side"), _as_str(raw.get("attack_side"), "Ngẫu nhiên")),
        )
        attack = AttackConfig(
            name=_as_str(raw.get("attack"), "Dragon_Attack"),
            side=_as_str(raw.get("attack_side"), recipe_cfg.side),
            sides=_as_str_list(raw.get("attack_sides")) or ["Ngẫu nhiên"],
            check_troops=_as_bool(raw.get("check_troops"), False),
            recipe=recipe_cfg,
        )

        return cls(
            resources=ResourceThresholds(
                gold=_as_int(raw.get("gold_threshold"), 65_000),
                elixir=_as_int(raw.get("elixir_threshold"), 65_000),
                dark_elixir=_as_int(raw.get("dark_elixir_threshold"), 0),
            ),
            upgrades=upgrades,
            attack=attack,
            training=TrainingConfig(
                mode=_as_str(raw.get("train_mode"), "smart"),
                quick_slot=_as_int(raw.get("quick_slot"), 1),
            ),
            clan=ClanConfig(
                enable_clan_games=_as_bool(raw.get("enable_clan_games"), False),
                enable_clan_capital=_as_bool(raw.get("enable_clan_capital"), False),
                capital_hall_level=_as_int(raw.get("capital_hall_level"), 9),
                request_troops=_as_bool(raw.get("request_troops"), True),
            ),
            vision=VisionConfig(
                redline_model=_as_str(raw.get("redline_model"), defaults.DEFAULT_YOLO_MODEL),
                redline_offset_ratio=_as_float(
                    raw.get("redline_offset_ratio"), defaults.DEFAULT_REDLINE_OFFSET_RATIO
                ),
                confidence=_as_float(raw.get("yolo_confidence"), defaults.DEFAULT_YOLO_CONFIDENCE),
                iou=_as_float(raw.get("yolo_iou"), defaults.DEFAULT_YOLO_IOU),
            ),
            auto_capture=AutoCaptureConfig(
                enabled=_as_bool(raw.get("auto_capture_dataset"), True),
                directory=_as_str(raw.get("auto_capture_dir"), defaults.DEFAULT_AUTO_CAPTURE_DIR),
                min_interval_sec=_as_float(
                    raw.get("auto_capture_min_interval_sec"),
                    defaults.DEFAULT_AUTO_CAPTURE_INTERVAL_SEC,
                ),
                max_files=_as_int(
                    raw.get("auto_capture_max_files"),
                    defaults.DEFAULT_AUTO_CAPTURE_MAX_FILES,
                ),
                only_on_fallback=_as_bool(raw.get("auto_capture_only_on_fallback"), True),
                success_sample=_as_float(raw.get("auto_capture_success_sample"), 0.1),
                scout_sample=_as_float(raw.get("auto_capture_scout_sample"), 1.0),
                on_scout=_as_bool(raw.get("auto_capture_on_scout"), True),
                on_attack=_as_bool(raw.get("auto_capture_on_attack"), False),
                image_format=_as_str(raw.get("auto_capture_format"), "jpg"),
                jpeg_quality=_as_int(
                    raw.get("auto_capture_jpeg_quality"),
                    defaults.DEFAULT_AUTO_CAPTURE_JPEG_QUALITY,
                ),
                webp_quality=_as_int(
                    raw.get("auto_capture_webp_quality"),
                    defaults.DEFAULT_AUTO_CAPTURE_WEBP_QUALITY,
                ),
                png_compression=_as_int(
                    raw.get("auto_capture_png_compression"),
                    defaults.DEFAULT_AUTO_CAPTURE_PNG_COMPRESSION,
                ),
            ),
            logging=LoggingConfig(
                level=_as_str(raw.get("log_level"), defaults.DEFAULT_LOG_LEVEL).upper(),
                file_enabled=_as_bool(raw.get("log_file_enabled"), True),
                file_path=_as_str(raw.get("log_file_path"), defaults.DEFAULT_LOG_FILE),
                max_bytes=_as_int(raw.get("log_max_bytes"), defaults.DEFAULT_LOG_MAX_BYTES),
                backup_count=_as_int(raw.get("log_backup_count"), defaults.DEFAULT_LOG_BACKUP_COUNT),
            ),
            emulator=EmulatorConfig(
                emulator_type=EmulatorType.from_value(raw.get("emulator_type")),
                host=_as_str(raw.get("emulator_host"), ""),
                ld_index=_as_int(raw.get("ld_index"), 0),
            ),
            enable_stats=_as_bool(raw.get("enable_stats"), False),
            schema_version=_as_int(raw.get("schema_version"), CONFIG_SCHEMA_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the config to the legacy flat ``settings.json`` shape."""
        wall = self.upgrades.wall
        return {
            "gold_threshold": self.resources.gold,
            "elixir_threshold": self.resources.elixir,
            "dark_elixir_threshold": self.resources.dark_elixir,
            "upgrade_wall": wall.enabled,
            "wall_level": wall.level,
            "wall_gold_threshold": wall.gold_threshold,
            "wall_elixir_threshold": wall.elixir_threshold,
            "upgrade_hero": self.upgrades.hero.enabled,
            "hero_priorities": list(self.upgrades.hero.priorities),
            "upgrade_defense": self.upgrades.defense.enabled,
            "defense_priorities": list(self.upgrades.defense.priorities),
            "upgrade_army": self.upgrades.army.enabled,
            "army_priorities": list(self.upgrades.army.priorities),
            "upgrade_resource": self.upgrades.resource.enabled,
            "resource_priorities": list(self.upgrades.resource.priorities),
            "upgrade_other": self.upgrades.other.enabled,
            "other_buildings": list(self.upgrades.other.priorities),
            "request_troops": self.clan.request_troops,
            "attack": self.attack.name,
            "recipe_name": self.attack.recipe.name,
            "recipe": {
                "troops": dict(self.attack.recipe.troops),
                "spells": dict(self.attack.recipe.spells),
                "siege": dict(self.attack.recipe.siege),
                "side": self.attack.recipe.side,
            },
            "attack_side": self.attack.side,
            "check_troops": self.attack.check_troops,
            "train_mode": self.training.mode,
            "quick_slot": self.training.quick_slot,
            "enable_clan_games": self.clan.enable_clan_games,
            "enable_clan_capital": self.clan.enable_clan_capital,
            "capital_hall_level": self.clan.capital_hall_level,
            "enable_stats": self.enable_stats,
            "redline_model": self.vision.redline_model,
            "redline_offset_ratio": self.vision.redline_offset_ratio,
            "yolo_confidence": self.vision.confidence,
            "yolo_iou": self.vision.iou,
            "auto_capture_dataset": self.auto_capture.enabled,
            "auto_capture_dir": self.auto_capture.directory,
            "auto_capture_min_interval_sec": self.auto_capture.min_interval_sec,
            "auto_capture_max_files": self.auto_capture.max_files,
            "auto_capture_only_on_fallback": self.auto_capture.only_on_fallback,
            "auto_capture_success_sample": self.auto_capture.success_sample,
            "auto_capture_scout_sample": self.auto_capture.scout_sample,
            "auto_capture_on_scout": self.auto_capture.on_scout,
            "auto_capture_on_attack": self.auto_capture.on_attack,
            "auto_capture_format": self.auto_capture.image_format,
            "auto_capture_jpeg_quality": self.auto_capture.jpeg_quality,
            "auto_capture_webp_quality": self.auto_capture.webp_quality,
            "auto_capture_png_compression": self.auto_capture.png_compression,
            "attack_sides": list(self.attack.sides),
            "log_level": self.logging.level,
            "log_file_enabled": self.logging.file_enabled,
            "log_file_path": self.logging.file_path,
            "log_max_bytes": self.logging.max_bytes,
            "log_backup_count": self.logging.backup_count,
            "emulator_type": self.emulator.emulator_type.value,
            "emulator_host": self.emulator.host,
            "ld_index": self.emulator.ld_index,
            "schema_version": self.schema_version,
        }
