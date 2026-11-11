"""Village / upgrade feature view (config-only for non-wall groups)."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from COCbot.core.config.schema import UpgradeConfig
from COCbot.features.village.targets import group_targets
from COCbot.features.village.viewmodel import PRIORITY_CATEGORIES, VillageViewModel
from COCbot.models.enums import UpgradeCategory
from COCbot.ui_components import Card, PrimaryButton, SecondaryButton, StatusLabel

_CATEGORY_LABELS = {
    UpgradeCategory.HERO: "Hero",
    UpgradeCategory.DEFENSE: "Defense",
    UpgradeCategory.ARMY: "Army",
    UpgradeCategory.RESOURCE: "Resource",
    UpgradeCategory.OTHER: "Other",
}


class VillageView(QWidget):
    """Edit wall upgrades and priority lists; no game logic lives here."""

    def __init__(self, viewmodel: VillageViewModel, parent: QWidget | None = None) -> None:
        """Build the village config panel and bind view-model signals."""
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._loading = False
        self._scan_allowed = True
        self._build_ui()
        self._connect_signals()
        self._viewmodel.loaded.connect(self._on_loaded)
        self._viewmodel.saved.connect(self._on_saved)
        self._viewmodel.dirty_changed.connect(self._on_dirty_changed)
        self._viewmodel.status_message.connect(self._on_status)
        self._viewmodel.error_occurred.connect(self._on_error)
        self._viewmodel.load()

    def _build_ui(self) -> None:
        """Create the wall and priority sub-tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("subTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_wall_tab(), "Wall")
        self.priority_checks: dict[UpgradeCategory, QCheckBox] = {}
        self.priority_edits: dict[UpgradeCategory, QLineEdit] = {}
        self.priority_lists: dict[UpgradeCategory, QListWidget] = {}
        for category in PRIORITY_CATEGORIES:
            self.tabs.addTab(self._build_priority_tab(category), _CATEGORY_LABELS[category])
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.status = StatusLabel()
        footer.addWidget(self.status, 1)
        self.scan_btn = SecondaryButton("Scan from game")
        self.scan_btn.setToolTip(
            "Open the in-game Buildings & Heroes panel and read the upgrade list"
        )
        self.defaults_btn = SecondaryButton("Defaults")
        self.reload_btn = SecondaryButton("Reload")
        self.save_btn = PrimaryButton("Save")
        self.save_btn.setEnabled(False)
        footer.addWidget(self.scan_btn)
        footer.addWidget(self.defaults_btn)
        footer.addWidget(self.reload_btn)
        footer.addWidget(self.save_btn)
        layout.addLayout(footer)

    def _build_wall_tab(self) -> QWidget:
        """Create the functional wall upgrade form."""
        card = Card(
            "Wall upgrade",
            "Spend overflow loot on walls automatically.",
        )
        self.wall_enabled = QCheckBox("Enable wall upgrade")
        self.wall_level = self._spin(1, 20, 1, 140)
        self.wall_gold = self._spin(0, 100_000_000, 100_000, 160)
        self.wall_elixir = self._spin(0, 100_000_000, 100_000, 160)
        card.add(self.wall_enabled)
        card.add_row("Target level", self.wall_level)
        card.add_row("Gold threshold", self.wall_gold)
        card.add_row("Elixir threshold", self.wall_elixir)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_priority_tab(self, category: UpgradeCategory) -> QWidget:
        """Create a priority group tab with checkable targets."""
        card = Card(
            f"{_CATEGORY_LABELS[category]} upgrades",
            "Tick the targets you want, or press Scan from game to read them.",
        )
        check = QCheckBox(f"Enable {_CATEGORY_LABELS[category].lower()} upgrades")
        targets = QListWidget()
        targets.setObjectName("upgradeTargets")
        targets.setSelectionMode(QListWidget.NoSelection)
        targets.setFixedHeight(118)
        edit = QLineEdit()
        edit.setPlaceholderText("Extra names, comma separated")
        card.add(check)
        card.add(targets)
        card.add_row("Extra", edit)
        self.priority_checks[category] = check
        self.priority_lists[category] = targets
        self.priority_edits[category] = edit
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    @staticmethod
    def _make_item(name: str, checked: bool) -> QListWidgetItem:
        """Create one checkable target row."""
        item = QListWidgetItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _fill_list(self, category: UpgradeCategory, names: list[str]) -> None:
        """Replace one category list with *names*, all checked."""
        widget = self.priority_lists[category]
        widget.blockSignals(True)
        try:
            widget.clear()
            for name in names:
                widget.addItem(self._make_item(name, True))
        finally:
            widget.blockSignals(False)

    @staticmethod
    def _spin(minimum: int, maximum: int, step: int, width: int) -> QSpinBox:
        """Create a configured spin box."""
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        widget.setMinimumWidth(width)
        return widget

    def _connect_signals(self) -> None:
        """Connect widgets to the bulk-apply handler."""
        for widget in (
            self.wall_level,
            self.wall_gold,
            self.wall_elixir,
        ):
            widget.valueChanged.connect(self._apply)
        self.wall_enabled.toggled.connect(self._apply)
        for check in self.priority_checks.values():
            check.toggled.connect(self._apply)
        for edit in self.priority_edits.values():
            edit.textChanged.connect(self._apply)
        for targets in self.priority_lists.values():
            targets.itemChanged.connect(self._apply)
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        self.save_btn.clicked.connect(self._viewmodel.save)
        self.reload_btn.clicked.connect(self._viewmodel.load)
        self.defaults_btn.clicked.connect(self._on_defaults)
        self._viewmodel.targets_scanned.connect(self._on_targets_scanned)
        self._viewmodel.scan_started.connect(self._on_scan_started)
        self._viewmodel.scan_finished.connect(self._on_scan_finished)

    def _on_scan_clicked(self) -> None:
        """Ask the view-model to read the in-game panel."""
        self._viewmodel.scan_targets()

    def _on_scan_started(self) -> None:
        """Lock the scan button while the panel read is running."""
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning…")

    def _on_scan_finished(self) -> None:
        """Restore the scan button when the thread exits."""
        self.scan_btn.setEnabled(self._scan_allowed)
        self.scan_btn.setText("Scan from game")

    def set_bot_running(self, running: bool) -> None:
        """Disable scanning while the bot drives the game."""
        self._scan_allowed = not running
        if not self._viewmodel.is_scanning:
            self.scan_btn.setEnabled(self._scan_allowed)
        self.scan_btn.setToolTip(
            "Stop the bot first" if running
            else "Open the in-game Buildings & Heroes panel and read the upgrade list"
        )

    def _on_targets_scanned(self, names: object) -> None:
        """Merge scanned names into the category lists."""
        groups = group_targets(names)
        for category, values in groups.items():
            widget = self.priority_lists[category]
            existing = {
                widget.item(index).text().lower()
                for index in range(widget.count())
            }
            added = False
            widget.blockSignals(True)
            try:
                for name in values:
                    if name.lower() in existing:
                        continue
                    widget.addItem(self._make_item(name, False))
                    existing.add(name.lower())
                    added = True
            finally:
                widget.blockSignals(False)
            if added:
                widget.sortItems()
        self._apply()

    def _apply(self, *_args: object) -> None:
        """Push widget values into the view-model draft."""
        if self._loading:
            return
        self._viewmodel.set_wall(
            self.wall_enabled.isChecked(),
            self.wall_level.value(),
            self.wall_gold.value(),
            self.wall_elixir.value(),
        )
        for category, check in self.priority_checks.items():
            priorities: list[str] = []
            widget = self.priority_lists[category]
            for index in range(widget.count()):
                item = widget.item(index)
                if item.checkState() == Qt.Checked:
                    priorities.append(item.text())
            known = {name.lower() for name in priorities}
            for part in self.priority_edits[category].text().split(","):
                name = part.strip()
                if name and name.lower() not in known:
                    priorities.append(name)
                    known.add(name.lower())
            self._viewmodel.set_priority(category, check.isChecked(), priorities)

    def _on_loaded(self, upgrades: object) -> None:
        """Render a loaded upgrade configuration."""
        if not isinstance(upgrades, UpgradeConfig):
            return
        self._loading = True
        try:
            self.wall_enabled.setChecked(upgrades.wall.enabled)
            self.wall_level.setValue(upgrades.wall.level)
            self.wall_gold.setValue(upgrades.wall.gold_threshold)
            self.wall_elixir.setValue(upgrades.wall.elixir_threshold)
            for category, check in self.priority_checks.items():
                group = self._viewmodel.priority_group(category)
                check.setChecked(group.enabled)
                self._fill_list(category, list(group.priorities))
                self.priority_edits[category].clear()
        finally:
            self._loading = False
        self.save_btn.setEnabled(self._viewmodel.is_dirty)

    def _on_saved(self, upgrades: object) -> None:
        """Disable Save after a successful write."""
        self.save_btn.setEnabled(False)

    def _on_dirty_changed(self, dirty: bool) -> None:
        """Enable Save only when the draft differs from disk."""
        self.save_btn.setEnabled(dirty)

    def _on_defaults(self) -> None:
        """Load defaults into the draft and re-render."""
        self._viewmodel.reset_defaults()
        self._on_loaded(self._viewmodel.config)

    def _on_status(self, message: str, kind: str) -> None:
        """Display a status line."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Display an error line."""
        self.status.show_message(message, "error")
