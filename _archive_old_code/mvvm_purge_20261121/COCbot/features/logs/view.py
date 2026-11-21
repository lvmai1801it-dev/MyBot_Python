"""Logs feature view: filterable table and export controls."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from COCbot.features.logs.model import LogEntry
from COCbot.features.logs.viewmodel import LogsViewModel
from COCbot.models.enums import LogLevel
from COCbot.ui_components import Card, SecondaryButton, StatusLabel

ALL_EVENTS = "All events"
_FILTER_LEVELS = (ALL_EVENTS, "INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG")
_LEVEL_COLORS = {
    LogLevel.DEBUG: "#657877",
    LogLevel.INFO: "#536D80",
    LogLevel.SUCCESS: "#13775F",
    LogLevel.WARNING: "#9A6B00",
    LogLevel.ERROR: "#A82921",
    LogLevel.CRITICAL: "#A82921",
}


class LogsView(QWidget):
    """Render structured BotEvent rows without owning any bot logic."""

    def __init__(self, viewmodel: LogsViewModel, parent: QWidget | None = None) -> None:
        """Build the log table and bind view-model signals."""
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._build_ui()
        self._connect_signals()
        self._viewmodel.refresh()

    def _build_ui(self) -> None:
        """Create filters, table, status, and export controls."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        card = Card("Bot log", "Structured events from the bot engine.")
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(list(_FILTER_LEVELS))
        self.filter_combo.setMinimumWidth(120)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search message or phase")
        self.clear_btn = SecondaryButton("Clear")
        self.export_btn = SecondaryButton("Export")
        controls.addWidget(self.filter_combo)
        controls.addWidget(self.search_edit, 1)
        controls.addWidget(self.clear_btn)
        controls.addWidget(self.export_btn)
        card.add_layout(controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Level", "Message", "Phase"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        card.add(self.table)
        layout.addWidget(card, 1)

        self.status = StatusLabel()
        layout.addWidget(self.status)

    def _connect_signals(self) -> None:
        """Connect filters/buttons and view-model signals."""
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        self.search_edit.textChanged.connect(self._on_filter_changed)
        self.clear_btn.clicked.connect(self._viewmodel.clear)
        self.export_btn.clicked.connect(self._on_export)
        self._viewmodel.entry_added.connect(self._append_entry)
        self._viewmodel.entries_loaded.connect(self._on_entries_loaded)
        self._viewmodel.entries_cleared.connect(self._on_cleared)
        self._viewmodel.status_message.connect(self._on_status)
        self._viewmodel.error_occurred.connect(self._on_error)

    def _on_filter_changed(self, *_args: object) -> None:
        """Apply the selected level/search filter."""
        text = self.filter_combo.currentText()
        level = None if text == ALL_EVENTS else LogLevel(text)
        self._viewmodel.set_filter(level, self.search_edit.text())

    def _append_entry(self, entry: object) -> None:
        """Append one row to the table."""
        if not isinstance(entry, LogEntry):
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = (
            entry.time_text,
            entry.level.value,
            entry.message,
            entry.phase.value,
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column in (0, 1, 3):
                item.setTextAlignment(Qt.AlignCenter)
            if column == 1:
                item.setForeground(QBrush(QColor(_LEVEL_COLORS.get(entry.level, "#193431"))))
            self.table.setItem(row, column, item)
        self.table.scrollToBottom()

    def _on_entries_loaded(self, entries: object) -> None:
        """Rebuild the table from a filtered snapshot."""
        if not isinstance(entries, (list, tuple)):
            return
        self.table.setRowCount(0)
        for entry in entries:
            self._append_entry(entry)

    def _on_cleared(self) -> None:
        """Clear the table."""
        self.table.setRowCount(0)

    def _on_export(self) -> None:
        """Ask for a destination and export the filtered rows."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export bot log",
            "bot_log.txt",
            "Text files (*.txt);;All files (*)",
        )
        if path:
            self._viewmodel.export(path)

    def _on_status(self, message: str, kind: str) -> None:
        """Display a status line."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Display an error line."""
        self.status.show_message(message, "error")
