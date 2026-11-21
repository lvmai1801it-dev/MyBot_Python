"""Unit tests for the ported legacy attack step."""

from __future__ import annotations

import unittest

from COCbot.app.orchestrator import CycleContext
from COCbot.app.session import BotSession
from COCbot.features.attack.legacy_step import LegacyAttackStep


class FakeStore:
    """Return a fixed config snapshot."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def get(self):
        """Return the stored config."""

        class _Cfg:
            def __init__(self, data: dict) -> None:
                self._data = data

            def to_dict(self) -> dict:
                """Return the legacy settings shape."""
                return dict(self._data)

        return _Cfg(self._payload)


class LegacyAttackStepTests(unittest.TestCase):
    """Verify the dry-run gate and stop-event bridging."""

    def test_dry_run_skips_the_battle(self) -> None:
        step = LegacyAttackStep(FakeStore({}), host="127.0.0.1:21503", execute=False)
        session = BotSession()
        session.start()
        result = step.run(CycleContext(session=session, config=None))
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("skipped"))

    def test_stop_event_is_restored_after_an_aborted_run(self) -> None:
        from COCbot.app import state

        # Execute mode, but request a stop up front: the step must leave
        # the legacy state events untouched after it returns.
        step = LegacyAttackStep(FakeStore({}), host="127.0.0.1:21503", execute=True)
        session = BotSession()
        session.start()
        session.request_stop()
        saved_stop = state.stop_event
        saved_pause = state.pause_event

        import unittest.mock as mock

        with mock.patch(
            "COCbot.game.battle.helpers.search_attack", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                step.run(CycleContext(session=session, config=None))

        self.assertIs(state.stop_event, saved_stop)
        self.assertIs(state.pause_event, saved_pause)


if __name__ == "__main__":
    unittest.main()
