"""Thread-safe holder for the current application configuration."""

from __future__ import annotations

import threading
from dataclasses import replace

from COCbot.core.config.schema import AppConfig


class ConfigStore:
    """Share one live :class:`AppConfig` between features and services."""

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialize the store with *config* or defaults."""
        self._config = config or AppConfig()
        self._lock = threading.RLock()

    def get(self) -> AppConfig:
        """Return the current configuration snapshot."""
        with self._lock:
            return self._config

    def set(self, config: AppConfig) -> None:
        """Replace the current configuration."""
        with self._lock:
            self._config = config

    def update(self, **changes: object) -> AppConfig:
        """Return and store a copy with top-level *changes* applied."""
        with self._lock:
            self._config = replace(self._config, **changes)
            return self._config
