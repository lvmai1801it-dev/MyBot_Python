"""Statistics feature view (layout + signal binding only)."""

from __future__ import annotations

import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from COCbot.features.statistics.model import StatisticsSnapshot, StatsTotals
from COCbot.features.statistics.viewmodel import StatisticsViewModel
from COCbot.ui_components import Card, DangerButton, SecondaryButton, StatusLabel


class StatisticsView(QWidget):
    """Render totals and per-village statistics."""

    def __init__(self, viewmodel: StatisticsViewModel, parent: QWidget | None = None) -> None:
        """Build the stats panel and bind view-model signals."""
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._build_ui()
        self._connect_signals()
        self._viewmodel.refresh()

    def _build_ui(self) -> None:
        """Create totals, per-village table, and controls."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        totals_card = Card("Total resources gain", "Loot and star counts across all villages.")
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        self.value_labels: dict[str, QLabel] = {}
        rows = (
            ("gold", "Gold"),
            ("elixir", "Elixir"),
            ("dark_elixir", "Dark elixir"),
            ("attacks", "Attacks"),
            ("stars", "Total stars"),
            ("star0", "0 stars"),
            ("star1", "1 star"),
            ("star2", "2 stars"),
            ("star3", "3 stars"),
        )
        for index, (key, title) in enumerate(rows):
            label = QLabel(title + ":")
            label.setObjectName("muted")
            value = QLabel("0")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(label, index // 2, (index % 2) * 2)
            grid.addWidget(value, index // 2, (index % 2) * 2 + 1)
            self.value_labels[key] = value
        self.value_labels["gold"].setStyleSheet("font-weight:600;")
        totals_card.add_layout(grid)
        layout.addWidget(totals_card)

        village_card = Card("Per village", "Stats_1.json … Stats_5.json in profiles/.")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Village", "Gold", "Elixir", "DE", "Attacks", "Stars", "Updated"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        village_card.add(self.table)
        layout.addWidget(village_card, 1)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.status = StatusLabel()
        controls.addWidget(self.status, 1)
        self.refresh_btn = SecondaryButton("Refresh")
        self.reset_btn = DangerButton("Reset stats")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.reset_btn)
        layout.addLayout(controls)

    def _connect_signals(self) -> None:
        """Connect buttons and view-model signals."""
        self.refresh_btn.clicked.connect(self._viewmodel.refresh)
        self.reset_btn.clicked.connect(self._on_reset)
        self._viewmodel.snapshot_loaded.connect(self._on_snapshot)
        self._viewmodel.status_message.connect(self._on_status)
        self._viewmodel.error_occurred.connect(self._on_error)
        self._viewmodel.busy_changed.connect(self._on_busy_changed)

    @staticmethod
    def _format(value: int) -> str:
        """Format an integer with thousands separators."""
        return f"{int(value):,}"

    def _on_snapshot(self, snapshot: object) -> None:
        """Render a statistics snapshot."""
        if not isinstance(snapshot, StatisticsSnapshot):
            return
        overall: StatsTotals = snapshot.overall
        self.value_labels["gold"].setText(self._format(overall.gold))
        self.value_labels["elixir"].setText(self._format(overall.elixir))
        self.value_labels["dark_elixir"].setText(self._format(overall.dark_elixir))
        self.value_labels["attacks"].setText(self._format(overall.attacks))
        self.value_labels["stars"].setText(self._format(overall.total_stars))
        for stars in range(4):
            self.value_labels[f"star{stars}"].setText(
                self._format(overall.star_count(stars))
            )

        self.table.setRowCount(0)
        for village in snapshot.villages:
            row = self.table.rowCount()
            self.table.insertRow(row)
            totals = village.totals
            updated = (
                time.strftime("%Y-%m-%d %H:%M", time.localtime(totals.last_update))
                if totals.last_update
                else "—"
            )
            values = (
                str(village.index),
                self._format(totals.gold),
                self._format(totals.elixir),
                self._format(totals.dark_elixir),
                self._format(totals.attacks),
                self._format(totals.total_stars),
                updated,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 4, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)
        self.status.show_message("Statistics loaded", "info")

    def _on_reset(self) -> None:
        """Confirm and reset every stats file."""
        answer = QMessageBox.question(
            self,
            "Reset statistics",
            "Reset all Stats_*.json files to zero?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._viewmodel.reset()

    def _on_status(self, message: str, kind: str) -> None:
        """Show a status line."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Show an error line."""
        self.status.show_message(message, "error")

    def _on_busy_changed(self, busy: bool) -> None:
        """Disable controls while loading/resetting."""
        self.refresh_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
