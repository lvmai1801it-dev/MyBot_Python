"""Unit tests for the pure-Python bot orchestrator."""

from __future__ import annotations

import unittest
from typing import Sequence

from COCbot.app.orchestrator import BotOrchestrator, CycleContext, StepResult
from COCbot.app.session import BotSession
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import BotPhase


class FakeClock:
    """Deterministic clock for loop tests."""

    def __init__(self) -> None:
        self._now = 0.0

    def now(self) -> float:
        return self._now

    def monotonic(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        self._now += max(0.0, seconds)


class FakeStep:
    """Configurable cycle step."""

    def __init__(
        self,
        name: str,
        success: bool = True,
        message: str = "",
        raises: Exception | None = None,
        phase: BotPhase | None = None,
        stop: bool = False,
    ) -> None:
        self._name = name
        self.success = success
        self.message = message
        self.raises = raises
        self.phase = phase
        self.stop = stop
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    def run(self, context: CycleContext) -> StepResult:
        self.calls += 1
        if self.stop:
            context.session.request_stop()
        if self.raises is not None:
            raise self.raises
        return StepResult(self.success, self.message, self.phase)


class FakeSink:
    """Collect events emitted by the orchestrator."""

    def __init__(self) -> None:
        self.events: list[BotEvent] = []

    def emit(self, event: BotEvent) -> None:
        self.events.append(event)


class OrchestratorCycleTests(unittest.TestCase):
    """Verify step ordering, failure accounting, and stop limits."""

    def test_successful_cycle(self) -> None:
        steps = [FakeStep("one", message="a"), FakeStep("two", message="b")]
        orchestrator = BotOrchestrator(steps, session=BotSession(), clock=FakeClock())
        result = orchestrator.run_cycle()
        self.assertTrue(result.completed)
        self.assertEqual(result.steps_run, 2)
        self.assertEqual(result.errors, 0)
        self.assertEqual(result.message, "b")

    def test_step_can_change_phase(self) -> None:
        steps = [FakeStep("attack", phase=BotPhase.ATTACKING)]
        session = BotSession()
        orchestrator = BotOrchestrator(steps, session=session, clock=FakeClock())
        orchestrator.run_cycle()
        self.assertEqual(session.status.phase, BotPhase.ATTACKING)

    def test_failure_stops_at_limit(self) -> None:
        step = FakeStep("bad", success=False, message="network down")
        session = BotSession()
        orchestrator = BotOrchestrator(
            [step],
            session=session,
            clock=FakeClock(),
            max_consecutive_errors=2,
        )
        first = orchestrator.run_cycle()
        self.assertEqual(first.errors, 1)
        self.assertFalse(session.stop_requested)

        second = orchestrator.run_cycle()
        self.assertEqual(second.errors, 1)
        self.assertTrue(session.stop_requested)

    def test_exception_is_counted(self) -> None:
        step = FakeStep("boom", raises=RuntimeError("exploded"))
        orchestrator = BotOrchestrator([step], clock=FakeClock())
        result = orchestrator.run_cycle()
        self.assertEqual(result.errors, 1)
        self.assertIn("exploded", result.message)

    def test_exception_resets_only_on_success(self) -> None:
        bad = FakeStep("bad", success=False, message="bad")
        good = FakeStep("good")
        orchestrator = BotOrchestrator(
            [bad, good],
            clock=FakeClock(),
            max_consecutive_errors=2,
        )
        orchestrator.run_cycle()
        self.assertEqual(orchestrator._consecutive_errors, 0)
        orchestrator.run_cycle()
        self.assertFalse(orchestrator.session.stop_requested)


class OrchestratorLoopTests(unittest.TestCase):
    """Verify run_forever emits lifecycle events and stops cleanly."""

    def test_run_forever_stops_on_session_request(self) -> None:
        sink = FakeSink()
        step = FakeStep("once", message="cycle done", stop=True)
        session = BotSession()
        orchestrator = BotOrchestrator(
            [step],
            session=session,
            clock=FakeClock(),
            cycle_delay=0,
        )
        orchestrator.run_forever(sink)
        self.assertFalse(orchestrator.is_running)
        self.assertFalse(session.status.is_running)
        self.assertEqual(session.status.phase, BotPhase.STOPPED)
        messages = [event.message for event in sink.events]
        self.assertIn("Bot started", messages)
        self.assertIn("Bot stopped", messages)
        self.assertIn("cycle done", messages)
        self.assertEqual(step.calls, 1)

    def test_broken_sink_does_not_crash(self) -> None:
        class BrokenSink:
            def emit(self, event: BotEvent) -> None:
                raise RuntimeError("ui gone")

        orchestrator = BotOrchestrator(
            [FakeStep("once", stop=True)],
            clock=FakeClock(),
            cycle_delay=0,
        )
        orchestrator.run_forever(BrokenSink())
        self.assertFalse(orchestrator.is_running)

    def test_stop_before_cycle(self) -> None:
        orchestrator = BotOrchestrator([FakeStep("never")], clock=FakeClock())
        orchestrator.request_stop()
        result = orchestrator.run_cycle()
        self.assertFalse(result.completed)
        self.assertEqual(result.steps_run, 0)


if __name__ == "__main__":
    unittest.main()
