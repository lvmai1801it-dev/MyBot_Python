# ==== COCbot/gui/widgets.py ====
"""Small reusable Qt widgets: stdout bridge and frameless title bar."""
import time

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget


class TimestampStream(QObject):
    """Qt‑thread‑safe stdout / stderr redirector emitting signal per line."""

    new_line = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._buf = ""

    def write(self, s: str):
        if not s:
            return
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                ts = time.strftime("%H:%M:%S")
                self.new_line.emit(f"{ts} • {line}")

    def flush(self):
        return


class TitleBar(QWidget):
    """Frameless-window title bar with drag and double-click maximize."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPos() - self.window().frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        parent = self.window()
        if hasattr(parent, "_toggle_maximized"):
            parent._toggle_maximized()
        super().mouseDoubleClickEvent(event)
