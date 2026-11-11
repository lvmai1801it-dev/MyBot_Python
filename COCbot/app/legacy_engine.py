"""Legacy farm engine adapter.

This intentionally reuses the pre-MVVM bot loop for gameplay (training,
collectors, wall/clan actions, search, attack, account switching) while the new
shell provides the UI, threading, and lifecycle. It is the compatibility bridge
until the clean gameplay port reaches parity.
"""

from __future__ import annotations

from COCbot.core.config.store import ConfigStore
from COCbot.core.ports import EventSinkPort, LoggerPort
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import BotPhase, LogLevel


class LegacyEngine:
    """Run the legacy ``bot_loop`` behind the BotEnginePort interface."""

    def __init__(self, store: ConfigStore, logger: LoggerPort | None = None) -> None:
        """Snapshot the config and prepare the legacy state bridge."""
        self._store = store
        self._logger = logger
        self._running = False
        self._sink: EventSinkPort | None = None

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
        try:
            from COCbot.app import state
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

    def request_pause(self) -> None:
        """Clear the legacy pause event."""
        from COCbot.app import state

        state.pause_event.clear()

    def request_resume(self) -> None:
        """Set the legacy pause event."""
        from COCbot.app import state

        state.pause_event.set()
