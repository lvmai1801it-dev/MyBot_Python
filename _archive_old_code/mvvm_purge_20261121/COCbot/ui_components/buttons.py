"""Reusable buttons with theme object names."""

from __future__ import annotations

from PyQt5.QtWidgets import QPushButton, QWidget


class PrimaryButton(QPushButton):
    """Filled primary action button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        """Create a primary button."""
        super().__init__(text, parent)
        self.setObjectName("primaryBtn")


class SecondaryButton(QPushButton):
    """Outlined secondary action button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        """Create a secondary button."""
        super().__init__(text, parent)


class DangerButton(QPushButton):
    """Destructive action button."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        """Create a danger button."""
        super().__init__(text, parent)
        self.setObjectName("stopBtn")
