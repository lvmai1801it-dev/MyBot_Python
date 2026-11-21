"""Top-of-window resource bar: gold, elixir, dark elixir, gems, builders."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from COCbot.features.village.resources import VillageResources
from COCbot.viewmodels.resource_bar import ResourceBarViewModel

_CELLS: tuple[tuple[str, str, str], ...] = (
    ("gold", "Gold", "#D9A21B"),
    ("elixir", "Elixir", "#C13AA8"),
    ("dark", "Dark", "#4A3C6B"),
    ("gems", "Gems", "#1F9F5A"),
    ("builders", "Builders", "#8A5A2B"),
)


def _format_number(value: int | None) -> str:
    """Format one counter with thousands separators."""
    return "—" if value is None else f"{value:,}"


def _format_builders(available: int | None, total: int | None) -> str:
    """Format the builder counter as ``available/total``."""
    if available is None or total is None:
        return "—"
    return f"{available}/{total}"


class ResourceBar(QWidget):
    """Compact always-visible readout of the village counters."""

    def __init__(
        self,
        viewmodel: ResourceBarViewModel,
        parent: QWidget | None = None,
    ) -> None:
        """Build the cells and connect the view-model signals."""
        super().__init__(parent)
        self.setObjectName("resourceBar")
        self.setFixedHeight(50)
        self._viewmodel = viewmodel

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(4)

        self._values: dict[str, QLabel] = {}
        for index, (key, caption, color) in enumerate(_CELLS):
            cell = QWidget()
            column = QVBoxLayout(cell)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(0)

            caption_label = QLabel(caption)
            caption_label.setObjectName("resCaption")
            value_label = QLabel("—")
            value_label.setObjectName("resValue")
            value_label.setStyleSheet(f"color: {color};")
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            column.addWidget(caption_label)
            column.addWidget(value_label)

            layout.addWidget(cell, 1)
            self._values[key] = value_label

            if index < len(_CELLS) - 1:
                separator = QFrame()
                separator.setObjectName("resSeparator")
                separator.setFixedWidth(1)
                layout.addWidget(separator)

        self._viewmodel.snapshot_updated.connect(self.apply)

    def apply(self, snapshot: object) -> None:
        """Render one snapshot."""
        if not isinstance(snapshot, VillageResources):
            return
        self._values["gold"].setText(_format_number(snapshot.gold))
        self._values["elixir"].setText(_format_number(snapshot.elixir))
        self._values["dark"].setText(_format_number(snapshot.dark_elixir))
        self._values["gems"].setText(_format_number(snapshot.gems))
        self._values["builders"].setText(
            _format_builders(snapshot.builders_available, snapshot.builders_total)
        )
