"""Thread-safe bot session state (pause / stop / counters).

This module is pure Python; it must not import PyQt5.
"""

from __future__ import annotations

import threading

from COCbot.models.bot_state import BotStatus
from COCbot.models.enums import BotPhase


class BotSession:
    """Own the pause/stop signals and status shared with the UI."""

    def __init__(self, status: BotStatus | None = None) -> None:
        """Create a session in the idle state."""
        self._status = status or BotStatus()
        self._stop_event = threading.Event()
        self._condition = threading.Condition(threading.RLock())
        self._paused = False

    @property
    def status(self) -> BotStatus:
        """Return the live status object (prefer :meth:`snapshot` for UI)."""
        return self._status

    def snapshot(self) -> BotStatus:
        """Return a copy safe to hand to another thread."""
        with self._condition:
            current = self._status
            return BotStatus(
                phase=current.phase,
                is_running=current.is_running,
                is_paused=current.is_paused,
                current_account=current.current_account,
                attacks_done=current.attacks_done,
                last_error=current.last_error,
            )

    @property
    def stop_requested(self) -> bool:
        """Return ``True`` once a stop has been requested."""
        return self._stop_event.is_set()

    @property
    def stop_event(self) -> threading.Event:
        """Return the cooperative stop event for long-running steps."""
        return self._stop_event

    @property
    def is_paused(self) -> bool:
        """Return ``True`` while the session is paused."""
        with self._condition:
            return self._paused

    def start(self) -> None:
        """Clear stop/pause flags and mark the session as running."""
        with self._condition:
            self._stop_event.clear()
            self._paused = False
            self._status.reset()
            self._status.is_running = True
            self._status.phase = BotPhase.STARTING
            self._condition.notify_all()

    def request_stop(self) -> None:
        """Request a cooperative stop and wake a paused loop."""
        with self._condition:
            self._stop_event.set()
            self._status.phase = BotPhase.STOPPING
            self._condition.notify_all()

    def request_pause(self) -> None:
        """Pause at the next safe point."""
        with self._condition:
            self._paused = True
            self._status.is_paused = True
            self._status.phase = BotPhase.PAUSED

    def request_resume(self) -> None:
        """Resume a paused session."""
        with self._condition:
            self._paused = False
            self._status.is_paused = False
            if self._status.is_running:
                self._status.phase = BotPhase.RUNNING
            self._condition.notify_all()

    def wait_until_resumed(self) -> bool:
        """Block while paused; return ``False`` when a stop is requested."""
        with self._condition:
            while self._paused and not self._stop_event.is_set():
                self._condition.wait(timeout=0.5)
            return not self._stop_event.is_set()

    def mark_phase(self, phase: BotPhase) -> None:
        """Update the current phase without touching pause/stop flags."""
        with self._condition:
            self._status.phase = phase

    def record_attack(self) -> int:
        """Increment the attack counter and return the new value."""
        with self._condition:
            self._status.attacks_done += 1
            return self._status.attacks_done

    def record_error(self, message: str) -> None:
        """Store the latest error message."""
        with self._condition:
            self._status.last_error = message

    def reset(self) -> None:
        """Return the session to a clean idle state."""
        with self._condition:
            self._stop_event.clear()
            self._paused = False
            self._status.reset()
            self._condition.notify_all()

    def finish(self) -> None:
        """Mark the session as stopped after the loop exits."""
        with self._condition:
            self._paused = False
            self._status.is_running = False
            self._status.is_paused = False
            self._status.phase = BotPhase.STOPPED
            self._condition.notify_all()


__all__ = ["BotSession"]
