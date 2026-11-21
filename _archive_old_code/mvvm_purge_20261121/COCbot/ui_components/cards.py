"""Reusable card container."""

from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class Card(QFrame):
    """White rounded card with an optional title and subtitle."""

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Create a card and expose its body layout."""
        super().__init__(parent)
        self.setObjectName("card")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            root.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("cardSub")
            subtitle_label.setWordWrap(True)
            root.addWidget(subtitle_label)

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(8)
        root.addLayout(self._body)

    @property
    def body(self) -> QVBoxLayout:
        """Return the layout where callers add widgets."""
        return self._body

    def add(self, widget: QWidget) -> None:
        """Append *widget* to the card body."""
        self._body.addWidget(widget)

    def add_layout(self, layout: Any) -> None:
        """Append a layout to the card body."""
        self._body.addLayout(layout)

    def add_row(self, label: str, widget: QWidget) -> QWidget:
        """Add a label/widget pair on one row and return the row container."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        text = QLabel(label)
        text.setObjectName("muted")
        layout.addWidget(text)
        layout.addStretch(1)
        layout.addWidget(widget)
        self._body.addWidget(row)
        return row
