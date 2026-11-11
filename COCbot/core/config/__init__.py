"""Configuration package: typed schema, paths, defaults, coordinates.

Public entry points are :func:`load_config` and :func:`save_config`. Both are
pure Python and safe to call from any thread.
"""

from __future__ import annotations

import json
from pathlib import Path

from COCbot.core.config.coordinates import NAV, SCREEN, NavigationPoints, ScreenConfig
from COCbot.core.config.defaults import (
    DEFAULT_ADB_TIMEOUT,
    DEFAULT_EMULATOR,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_TAP_DURATION_MS,
    DEFAULT_YOLO_CONFIDENCE,
    DEFAULT_YOLO_MODEL,
    EMULATOR_HOSTS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from COCbot.core.config.paths import ProjectPaths, get_project_paths, resolve_src_dir
from COCbot.core.config.store import ConfigStore
from COCbot.core.config.schema import (
    AppConfig,
    AttackConfig,
    AutoCaptureConfig,
    ClanConfig,
    EmulatorConfig,
    LoggingConfig,
    PriorityUpgradeConfig,
    RecipeConfig,
    ResourceThresholds,
    TrainingConfig,
    UpgradeConfig,
    VisionConfig,
    WallUpgradeConfig,
)
from COCbot.core.config.version import APP_NAME, APP_VERSION, CONFIG_SCHEMA_VERSION

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "CONFIG_SCHEMA_VERSION",
    "DEFAULT_ADB_TIMEOUT",
    "DEFAULT_EMULATOR",
    "DEFAULT_LOG_FILE",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_TAP_DURATION_MS",
    "DEFAULT_YOLO_CONFIDENCE",
    "DEFAULT_YOLO_MODEL",
    "EMULATOR_HOSTS",
    "NAV",
    "SCREEN",
    "SCREEN_HEIGHT",
    "SCREEN_WIDTH",
    "AppConfig",
    "AttackConfig",
    "AutoCaptureConfig",
    "ClanConfig",
    "ConfigStore",
    "EmulatorConfig",
    "LoggingConfig",
    "NavigationPoints",
    "PriorityUpgradeConfig",
    "ProjectPaths",
    "RecipeConfig",
    "ResourceThresholds",
    "ScreenConfig",
    "TrainingConfig",
    "UpgradeConfig",
    "VisionConfig",
    "WallUpgradeConfig",
    "get_project_paths",
    "load_config",
    "resolve_src_dir",
    "save_config",
]


def load_config(path: Path | str | None = None) -> AppConfig:
    """Load ``settings.json`` and return a typed :class:`AppConfig`.

    Missing or malformed files fall back to defaults; a malformed file is never
    allowed to crash the GUI at startup.
    """
    settings_path = Path(path) if path is not None else get_project_paths().settings_json
    if not settings_path.is_file():
        return AppConfig()
    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig()
    if not isinstance(raw, dict):
        return AppConfig()
    return AppConfig.from_legacy_dict(raw)


def save_config(config: AppConfig, path: Path | str | None = None) -> None:
    """Atomically persist *config* to ``settings.json``."""
    settings_path = Path(path) if path is not None else get_project_paths().settings_json
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2)
    temp_path = settings_path.with_suffix(settings_path.suffix + ".tmp")
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(settings_path)
