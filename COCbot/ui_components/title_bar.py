"""Frameless-window drag surface for the application header."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget


class TitleBar(QWidget):
    """Draggable header area for a frameless main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the drag surface."""
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_pos = None

    def mousePressEvent(self, event) -> None:
        """Start dragging on left-click."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Move the window while the left button is held."""
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Stop dragging."""
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Delegate maximize to the window when it supports it."""
        parent = self.window()
        toggle = getattr(parent, "_toggle_maximized", None)
        if toggle is not None:
            toggle()
        super().mouseDoubleClickEvent(event)
