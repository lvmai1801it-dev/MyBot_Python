"""Bot orchestration loop built from injected cycle steps.

The orchestrator is pure Python (no Qt). Feature packages provide
:class:`CycleStep` implementations; the application layer only sequences them,
handles pause/stop, and forwards structured events to the UI.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence, runtime_checkable

from COCbot.app.session import BotSession
from COCbot.core.clock import SystemClock
from COCbot.core.config.defaults import (
    DEFAULT_CYCLE_DELAY_SEC,
    DEFAULT_MAX_CONSECUTIVE_ERRORS,
)
from COCbot.core.config.schema import AppConfig
from COCbot.core.ports import ClockPort, EventSinkPort, LoggerPort
from COCbot.models.bot_state import BotEvent, CycleResult
from COCbot.models.enums import BotPhase, LogLevel

_LOG_METHOD = {
    LogLevel.DEBUG: "debug",
    LogLevel.INFO: "info",
    LogLevel.SUCCESS: "info",
    LogLevel.WARNING: "warning",
    LogLevel.ERROR: "error",
    LogLevel.CRITICAL: "error",
}


@dataclass(frozen=True)
class StepResult:
    """Result returned by a single :class:`CycleStep`."""

    success: bool
    message: str = ""
    phase: BotPhase | None = None
    data: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CycleContext:
    """Dependencies passed to every step of a cycle."""

    session: BotSession
    config: AppConfig
    logger: LoggerPort | None = None


@runtime_checkable
class CycleStep(Protocol):
    """One unit of work inside a bot cycle."""

    @property
    def name(self) -> str:
        """Return a stable step name for logs and diagnostics."""

    def run(self, context: CycleContext) -> StepResult:
        """Execute the step and return its outcome."""


class BotOrchestrator:
    """Sequence feature steps into a repeatable bot loop."""

    def __init__(
        self,
        steps: Sequence[CycleStep],
        session: BotSession | None = None,
        config: AppConfig | None = None,
        logger: LoggerPort | None = None,
        clock: ClockPort | None = None,
        event_sink: EventSinkPort | None = None,
        cycle_delay: float = DEFAULT_CYCLE_DELAY_SEC,
        max_consecutive_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS,
    ) -> None:
        """Create an orchestrator from an ordered list of steps."""
        self._steps = list(steps)
        self._session = session or BotSession()
        self._config = config or AppConfig()
        self._logger = logger
        self._clock = clock or SystemClock()
        self._sink = event_sink
        self._cycle_delay = max(0.0, float(cycle_delay))
        self._max_consecutive_errors = max(1, int(max_consecutive_errors))
        self._consecutive_errors = 0
        self._running = False
        self._run_lock = threading.RLock()

    @property
    def session(self) -> BotSession:
        """Return the shared session object."""
        return self._session

    @property
    def is_running(self) -> bool:
        """Return ``True`` while :meth:`run_forever` is active."""
        with self._run_lock:
            return self._running

    def _emit(
        self,
        level: LogLevel,
        message: str,
        phase: BotPhase | None = None,
        data: Mapping[str, object] | None = None,
    ) -> None:
        """Log and publish one structured event."""
        event = BotEvent(
            level=level,
            message=message,
            phase=phase or self._session.status.phase,
            data=dict(data or {}),
        )
        if self._logger is not None:
            method = getattr(self._logger, _LOG_METHOD[level], self._logger.info)
            method(message)
        if self._sink is not None:
            try:
                self._sink.emit(event)
            except Exception as exc:  # a broken UI sink must not kill the bot
                if self._logger is not None:
                    self._logger.warning(f"Event sink failed: {exc}")

    def _register_failure(self, step_name: str, message: str) -> None:
        """Track consecutive failures and request a stop at the limit."""
        self._consecutive_errors += 1
        self._session.record_error(message)
        self._emit(LogLevel.ERROR, message, data={"step": step_name})
        if self._consecutive_errors >= self._max_consecutive_errors:
            self._emit(
                LogLevel.ERROR,
                f"Stopping after {self._consecutive_errors} consecutive errors",
            )
            self._session.request_stop()

    def run_cycle(self) -> CycleResult:
        """Run every step once, honoring pause/stop and error limits."""
        if self._session.stop_requested:
            return CycleResult(completed=False, message="stop requested")
        if not self._session.wait_until_resumed():
            return CycleResult(completed=False, message="stopped while paused")

        self._session.mark_phase(BotPhase.RUNNING)
        started = self._clock.monotonic()
        errors = 0
        steps_run = 0
        last_message = ""
        context = CycleContext(
            session=self._session,
            config=self._config,
            logger=self._logger,
        )

        for step in self._steps:
            if self._session.stop_requested:
                break
            if not self._session.wait_until_resumed():
                break
            name = step.name
            steps_run += 1
            try:
                result = step.run(context)
            except Exception as exc:
                errors += 1
                failure = f"{name} raised {type(exc).__name__}: {exc}"
                last_message = failure
                self._register_failure(name, failure)
                if self._logger is not None:
                    self._logger.exception(f"Step {name} failed")
                if self._session.stop_requested:
                    break
                continue

            if result.phase is not None:
                self._session.mark_phase(result.phase)
            if result.message:
                last_message = result.message
                self._emit(
                    LogLevel.INFO if result.success else LogLevel.WARNING,
                    result.message,
                    data={"step": name},
                )

            if not result.success:
                errors += 1
                self._register_failure(name, result.message or f"{name} failed")
                if self._session.stop_requested:
                    break
            else:
                self._consecutive_errors = 0

        duration = self._clock.monotonic() - started
        return CycleResult(
            completed=not self._session.stop_requested,
            steps_run=steps_run,
            errors=errors,
            duration=duration,
            message=last_message,
        )

    def run_forever(self, sink: EventSinkPort | None = None) -> None:
        """Run cycles until stopped; used by the QThread worker."""
        if sink is not None:
            self._sink = sink
        with self._run_lock:
            if self._running:
                return
            self._running = True

        self._session.start()
        self._emit(LogLevel.INFO, "Bot started")
        try:
            while not self._session.stop_requested:
                if not self._session.wait_until_resumed():
                    break
                self.run_cycle()
                if self._session.stop_requested:
                    break
                if self._consecutive_errors >= self._max_consecutive_errors:
                    break
                self._clock.sleep(self._cycle_delay)
        finally:
            with self._run_lock:
                self._running = False
            self._session.finish()
            self._emit(LogLevel.INFO, "Bot stopped")

    def request_stop(self) -> None:
        """Ask the loop to stop after the current step."""
        self._session.request_stop()

    def request_pause(self) -> None:
        """Ask the loop to pause at the next safe point."""
        self._session.request_pause()

    def request_resume(self) -> None:
        """Resume a paused loop."""
        self._session.request_resume()
