# ==== COCbot/gui/services/qt_thread.py ====
from PyQt5.QtCore import QThread
import traceback


class QtThreadCompat(QThread):
    """
    A QThread that mimics the API of threading.Thread just enough for
    existing GUI code (.join, .is_alive, .daemon) to keep working.
    """

    def __init__(self, target, args=(), kwargs=None, parent=None):
        super().__init__(parent)
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self.daemon = True

    def run(self):
        try:
            self._target(*self._args, **self._kwargs)
        except Exception as e:
            print(f"\n[THREAD] ⚠️ Worker crash: {e}")
            traceback.print_exc()

    def join(self, timeout=None):
        msec = -1 if timeout is None else int(timeout * 1000)
        self.wait(msec)

    def is_alive(self):
        return self.isRunning()
