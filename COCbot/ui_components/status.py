"""Inline status message label."""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QWidget

from COCbot.ui_components import theme

_STYLES = {
    "info": f"color: {theme.TEXT_MUTED};",
    "success": f"color: {theme.SUCCESS_TEXT};",
    "warning": f"color: {theme.WARNING_TEXT};",
    "error": f"color: {theme.ERROR_TEXT};",
}


class StatusLabel(QLabel):
    """Small label used for save/validation feedback."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create an empty status label."""
        super().__init__("", parent)
        self.setWordWrap(True)
        self.show_message("", "info")

    def show_message(self, text: str, kind: str = "info") -> None:
        """Display *text* with a colour matching *kind*."""
        self.setText(text)
        self.setStyleSheet(_STYLES.get(kind, _STYLES["info"]))

    def clear_message(self) -> None:
        """Remove the current message."""
        self.show_message("", "info")
