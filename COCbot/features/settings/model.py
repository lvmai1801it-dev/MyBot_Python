"""Settings feature domain model (pure Python)."""

from __future__ import annotations

from pathlib import Path

from COCbot.core.config import AppConfig, load_config, save_config
from COCbot.core.config.paths import get_project_paths
from COCbot.core.errors import StorageError
from COCbot.models.enums import EmulatorType

ATTACK_CHOICES: tuple[str, ...] = (
    "Dragon_Attack",
    "ElectroDragon_Attack",
)

SIDE_CHOICES: tuple[str, ...] = (
    "Ngẫu nhiên",
    "Trên Trái (TL)",
    "Trên Phải (TR)",
    "Dưới Trái (BL)",
    "Dưới Phải (BR)",
    "Nửa Trên (TL + TR)",
    "Nửa Dưới (BL + BR)",
    "Cả 4 hướng (+)",
)

EMULATOR_CHOICES: tuple[EmulatorType, ...] = (
    EmulatorType.MEMU,
    EmulatorType.LDPLAYER,
    EmulatorType.BLUESTACKS,
)

LOG_LEVEL_CHOICES: tuple[str, ...] = (
    "DEBUG",
    "INFO",
    "SUCCESS",
    "WARNING",
    "ERROR",
)


class SettingsModel:
    """Load, persist, and reset :class:`AppConfig`."""

    def __init__(self, settings_path: Path | str | None = None) -> None:
        """Use the project ``settings.json`` unless an explicit path is given."""
        self._path = (
            Path(settings_path)
            if settings_path is not None
            else get_project_paths().settings_json
        )

    @property
    def path(self) -> Path:
        """Return the settings file path."""
        return self._path

    def load(self) -> AppConfig:
        """Load settings, falling back to defaults for missing/broken files."""
        return load_config(self._path)

    def save(self, config: AppConfig) -> None:
        """Persist *config* atomically, wrapping filesystem errors."""
        try:
            save_config(config, self._path)
        except OSError as exc:
            raise StorageError(f"Could not save settings: {exc}") from exc

    def reset(self) -> AppConfig:
        """Return a fresh default configuration (not written until saved)."""
        return AppConfig()
