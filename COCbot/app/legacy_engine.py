"""Legacy farm engine adapter.

This intentionally reuses the pre-MVVM bot loop for gameplay (training,
collectors, wall/clan actions, search, attack, account switching) while the new
shell provides the UI, threading, and lifecycle. It is the compatibility bridge
until the clean gameplay port reaches parity.
"""

from __future__ import annotations

from typing import Callable

from COCbot.core.config.store import ConfigStore
from COCbot.core.ports import EventSinkPort, LoggerPort
from COCbot.features.village.resources import ResourceReader, VillageResources
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import BotPhase, LogLevel


class LegacyEngine:
    """Run the legacy ``bot_loop`` behind the BotEnginePort interface."""

    def __init__(
        self,
        store: ConfigStore,
        logger: LoggerPort | None = None,
        resource_reader: ResourceReader | None = None,
        on_resources: Callable[[VillageResources], None] | None = None,
    ) -> None:
        """Snapshot the config and prepare the legacy state bridge."""
        self._store = store
        self._logger = logger
        self._running = False
        self._sink: EventSinkPort | None = None
        self._resource_reader = resource_reader
        self._on_resources = on_resources

    @property
    def is_running(self) -> bool:
        """Return ``True`` while the legacy loop is active."""
        return self._running

    def _emit(self, level: LogLevel, message: str) -> None:
        """Publish one event to the UI and the file logger."""
        if self._logger is not None:
            method = {
                LogLevel.INFO: self._logger.info,
                LogLevel.SUCCESS: self._logger.info,
                LogLevel.WARNING: self._logger.warning,
                LogLevel.ERROR: self._logger.error,
                LogLevel.DEBUG: self._logger.debug,
            }.get(level, self._logger.info)
            method(message)
        if self._sink is not None:
            try:
                self._sink.emit(
                    BotEvent(level=level, message=message, phase=BotPhase.RUNNING)
                )
            except Exception:
                pass

    def run_forever(self, sink: EventSinkPort | None = None) -> None:
        """Run the legacy loop until the shared stop event is set."""
        self._sink = sink
        self._running = True
        self._emit(LogLevel.INFO, "Legacy farm engine starting")
        from COCbot.app import state

        state.resource_hook = self._publish_resources
        try:
            from COCbot.app.bootstrap import bot_loop

            state.stop_event.clear()
            state.pause_event.set()
            bot_loop(self._store.get().to_dict())
        except Exception as exc:
            self._emit(
                LogLevel.ERROR,
                f"Legacy farm engine failed: {type(exc).__name__}: {exc}",
            )
        finally:
            state.resource_hook = None
            self._running = False
            self._emit(LogLevel.INFO, "Legacy farm engine stopped")

    def run_cycle(self) -> None:
        """Run one legacy cycle (used by diagnostics)."""
        self._running = True
        try:
            from COCbot.app.bootstrap import one_cycle

            one_cycle(self._store.get().to_dict())
        finally:
            self._running = False

    def request_stop(self) -> None:
        """Set the legacy stop event."""
        from COCbot.app import state

        state.stop_event.set()
        state.pause_event.set()

    def _publish_resources(self, legacy: dict | None = None) -> None:
        """Merge the legacy readout with a fresh builder/gem read."""
        snapshot: VillageResources | None = None
        if self._resource_reader is not None:
            try:
                snapshot = self._resource_reader.read()
            except Exception as exc:
                self._emit(
                    LogLevel.WARNING,
                    f"Resource readout failed: {type(exc).__name__}: {exc}",
                )
        legacy = legacy or {}

        def pick_currency(attribute: str, key: str) -> int | None:
            raw = legacy.get(key)
            if raw is not None:
                try:
                    parsed = int(raw)
                except (TypeError, ValueError):
                    parsed = 0
                if parsed > 0:
                    return parsed
            return getattr(snapshot, attribute, None) if snapshot is not None else None

        merged = VillageResources(
            gold=pick_currency("gold", "gold"),
            elixir=pick_currency("elixir", "elixir"),
            dark_elixir=pick_currency("dark_elixir", "dark_elixir"),
            gems=getattr(snapshot, "gems", None) if snapshot is not None else None,
            builders_available=getattr(snapshot, "builders_available", None)
            if snapshot is not None
            else None,
            builders_total=getattr(snapshot, "builders_total", None)
            if snapshot is not None
            else None,
        )
        if merged.has_values() and self._on_resources is not None:
            try:
                self._on_resources(merged)
            except Exception as exc:
                self._emit(
                    LogLevel.WARNING,
                    f"Resource readout publish failed: {type(exc).__name__}: {exc}",
                )

    def request_pause(self) -> None:
        """Clear the legacy pause event."""
        from COCbot.app import state

        state.pause_event.clear()

    def request_resume(self) -> None:
        """Set the legacy pause event."""
        from COCbot.app import state

        state.pause_event.set()
