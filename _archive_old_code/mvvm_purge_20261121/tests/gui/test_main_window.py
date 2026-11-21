"""Offscreen GUI smoke test for the MVVM shell window."""

from __future__ import annotations

import threading
import time
import unittest

from PyQt5.QtWidgets import QApplication, QTabWidget, QWidget

from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import LogLevel
from COCbot.ui_components import apply_theme
from COCbot.viewmodels.main_viewmodel import MainViewModel
from COCbot.views.main_window import MainWindow

_APP = QApplication.instance() or QApplication([])


class FakeEngine:
    """Engine stub that blocks until stopped."""

    def __init__(self) -> None:
        self.stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return not self.stop_event.is_set()

    def run_forever(self, sink=None) -> None:
        if sink is not None:
            sink.emit(BotEvent(level=LogLevel.INFO, message="shell loop"))
        self.stop_event.wait(5)

    def run_cycle(self):
        return None

    def request_stop(self) -> None:
        self.stop_event.set()

    def request_pause(self) -> None:
        pass

    def request_resume(self) -> None:
        pass


class MainWindowTests(unittest.TestCase):
    """Verify tabs and run controls without blocking the GUI thread."""

    def setUp(self) -> None:
        apply_theme(_APP)
        self.engine = FakeEngine()
        self.vm = MainViewModel(self.engine)
        self.window = MainWindow(
            QWidget(),
            QWidget(),
            QWidget(),
            QWidget(),
            QWidget(),
            QWidget(),
            QWidget(),
            self.vm,
        )
        self.window.show()
        _APP.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        _APP.processEvents()

    def test_tabs_and_initial_state(self) -> None:
        tabs = self.window.findChild(QTabWidget)
        self.assertIsNotNone(tabs)
        self.assertEqual(tabs.count(), 7)
        self.assertTrue(self.window.start_btn.isEnabled())
        self.assertFalse(self.window.stop_btn.isEnabled())

    def test_start_stop_buttons(self) -> None:
        self.window.start_btn.click()
        worker = self.vm._worker
        self.assertIsNotNone(worker)
        for _ in range(20):
            _APP.processEvents()
            time.sleep(0.005)
        self.assertFalse(self.window.start_btn.isEnabled())
        self.assertTrue(self.window.stop_btn.isEnabled())

        self.window.stop_btn.click()
        self.assertTrue(worker.wait(5000))
        for _ in range(20):
            _APP.processEvents()
            time.sleep(0.005)
        self.assertTrue(self.window.start_btn.isEnabled())
        self.assertFalse(self.window.stop_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
