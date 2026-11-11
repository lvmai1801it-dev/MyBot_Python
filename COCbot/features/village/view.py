"""Village upgrade view: one sub-tab per in-game Build panel tab."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from COCbot.core.config.schema import UpgradeConfig
from COCbot.features.village.viewmodel import PRIORITY_CATEGORIES, VillageViewModel
from COCbot.models.enums import UpgradeCategory
from COCbot.ui_components import Card, PrimaryButton, SecondaryButton, StatusLabel

_CATEGORY_LABELS = {
    UpgradeCategory.BUILDINGS: "Buildings & Heroes",
    UpgradeCategory.ARMY: "Army Upgrades",
    UpgradeCategory.EQUIPMENT: "Hero Equipment",
    UpgradeCategory.PETS: "Hero Pets",
}

_TAB_CATEGORIES = {
    "buildings": UpgradeCategory.BUILDINGS,
    "army": UpgradeCategory.ARMY,
    "equipment": UpgradeCategory.EQUIPMENT,
    "pets": UpgradeCategory.PETS,
}


class VillageView(QWidget):
    """Edit walls and the scanned Build-panel targets; no game logic lives here."""

    def __init__(self, viewmodel: VillageViewModel, parent: QWidget | None = None) -> None:
        """Build the village config panel and bind view-model signals."""
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._loading = False
        self._scan_allowed = True
        self._builders: int | None = None
        self._build_ui()
        self._connect_signals()
        self._viewmodel.loaded.connect(self._on_loaded)
        self._viewmodel.saved.connect(self._on_saved)
        self._viewmodel.dirty_changed.connect(self._on_dirty_changed)
        self._viewmodel.status_message.connect(self._on_status)
        self._viewmodel.error_occurred.connect(self._on_error)
        self._viewmodel.load()

    def _build_ui(self) -> None:
        """Create one sub-tab per Build panel tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("subTabs")
        self.tabs.setDocumentMode(True)
        self.priority_checks: dict[UpgradeCategory, QCheckBox] = {}
        self.priority_edits: dict[UpgradeCategory, QLineEdit] = {}
        self.priority_lists: dict[UpgradeCategory, QListWidget] = {}
        self.priority_flags: dict[UpgradeCategory, QCheckBox] = {}
        for category in PRIORITY_CATEGORIES:
            self.tabs.addTab(
                self._build_priority_tab(category),
                _CATEGORY_LABELS[category].replace("&", "&&"),
            )
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.status = StatusLabel()
        footer.addWidget(self.status, 1)
        self.scan_btn = SecondaryButton("Scan from game")
        self.scan_btn.setToolTip(
            "Open the in-game Build panel and scan all four tabs"
        )
        self.upgrade_btn = PrimaryButton("Upgrade now")
        self.upgrade_btn.setToolTip(
            "Upgrade the ticked targets until they leave the Build panel"
        )
        self.upgrade_btn.setEnabled(True)
        self.defaults_btn = SecondaryButton("Defaults")
        self.reload_btn = SecondaryButton("Reload")
        self.save_btn = PrimaryButton("Save")
        self.save_btn.setEnabled(False)
        footer.addWidget(self.scan_btn)
        footer.addWidget(self.upgrade_btn)
        footer.addWidget(self.defaults_btn)
        footer.addWidget(self.reload_btn)
        footer.addWidget(self.save_btn)
        layout.addLayout(footer)

    def _build_wall_card(self, card: Card) -> None:
        """Add the wall controls (they live in the Buildings & Heroes tab)."""
        self.wall_enabled = QCheckBox("Upgrade walls")
        self.wall_level = self._spin(1, 20, 1, 120)
        self.wall_gold = self._spin(0, 100_000_000, 100_000, 150)
        self.wall_elixir = self._spin(0, 100_000_000, 100_000, 150)
        note = QLabel("One builder is kept free for walls when enabled.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        card.add(self.wall_enabled)
        card.add(note)
        self.builders_label = QLabel("Builders free: unknown — press Scan from game")
        self.builders_label.setObjectName("cardSub")
        self.builders_label.setWordWrap(True)
        card.add(self.builders_label)
        card.add_row("Wall level", self.wall_level)
        card.add_row("Gold threshold", self.wall_gold)
        card.add_row("Elixir threshold", self.wall_elixir)

    def _build_priority_tab(self, category: UpgradeCategory) -> QWidget:
        """Create a target tab with a checkable list."""
        label = _CATEGORY_LABELS[category]
        card = Card(
            f"{label} upgrades",
            "Tick the targets you want, or press Scan from game to read them.",
        )
        check = QCheckBox(
            "Enable "
            f"{_CATEGORY_LABELS[category].replace('&', 'and').lower()} upgrades"
        )
        targets = QListWidget()
        targets.setObjectName("upgradeTargets")
        targets.setSelectionMode(QListWidget.NoSelection)
        targets.setFixedHeight(118)
        edit = QLineEdit()
        edit.setPlaceholderText("Extra names, comma separated")
        card.add(check)
        if category is UpgradeCategory.BUILDINGS:
            self._build_wall_card(card)
            self.hero_priority = QCheckBox("Priority — heroes first")
            self.money_priority = QCheckBox("Priority — money buildings first")
            card.add(self.hero_priority)
            card.add(self.money_priority)
        else:
            flag = QCheckBox("Priority — upgrade this tab first")
            card.add(flag)
            self.priority_flags[category] = flag
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
    def _spin(minimum: int, maximum: int, step: int, width: int) -> QSpinBox:
        """Create a configured spin box."""
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        widget.setMinimumWidth(width)
        return widget

    def _connect_signals(self) -> None:
        """Connect widgets to the bulk-apply handler."""
        for widget in (self.wall_level, self.wall_gold, self.wall_elixir):
            widget.valueChanged.connect(self._apply)
        self.wall_enabled.toggled.connect(self._apply)
        self.hero_priority.toggled.connect(self._apply)
        self.money_priority.toggled.connect(self._apply)
        for check in self.priority_checks.values():
            check.toggled.connect(self._apply)
        for edit in self.priority_edits.values():
            edit.textChanged.connect(self._apply)
        for targets in self.priority_lists.values():
            targets.itemChanged.connect(self._on_item_changed)
        for flag in self.priority_flags.values():
            flag.toggled.connect(self._apply)
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        self.upgrade_btn.clicked.connect(self._on_upgrade_clicked)
        self.save_btn.clicked.connect(self._viewmodel.save)
        self.reload_btn.clicked.connect(self._viewmodel.load)
        self.defaults_btn.clicked.connect(self._on_defaults)
        self._viewmodel.targets_scanned.connect(self._on_targets_scanned)
        self._viewmodel.builders_updated.connect(self._on_builders_updated)
        self._viewmodel.scan_started.connect(self._on_scan_started)
        self._viewmodel.scan_finished.connect(self._on_scan_finished)
        self._viewmodel.upgrade_started.connect(self._on_upgrade_started)
        self._viewmodel.upgrade_finished.connect(self._on_upgrade_finished)

    def _allowance(self) -> int | None:
        """Return how many building targets may be ticked right now."""
        if self._builders is None:
            return None
        reserved = 1 if self.wall_enabled.isChecked() else 0
        return max(0, self._builders - reserved)

    def _checked_items(self, category: UpgradeCategory) -> list[QListWidgetItem]:
        """Return the ticked rows of one category."""
        widget = self.priority_lists[category]
        return [
            widget.item(index)
            for index in range(widget.count())
            if widget.item(index).checkState() == Qt.Checked
        ]

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        """Apply the builder limit while ticking targets."""
        if self._loading:
            return
        self._apply()

    def _enforce_limit(self) -> None:
        """Untick building targets beyond the free builder count."""
        limit = self._allowance()
        if limit is None:
            return
        widget = self.priority_lists[UpgradeCategory.BUILDINGS]
        checked = self._checked_items(UpgradeCategory.BUILDINGS)
        if len(checked) <= limit:
            return
        widget.blockSignals(True)
        try:
            for item in checked[limit:]:
                item.setCheckState(Qt.Unchecked)
        finally:
            widget.blockSignals(False)
        self.status.show_message(
            f"Only {limit} builder(s) free — kept the first {limit} target(s)",
            "warning",
        )

    def _update_builders_label(self) -> None:
        """Refresh the free-builder hint above the target list."""
        if self._builders is None:
            self.builders_label.setText(
                "Builders free: unknown — press Scan from game"
            )
            return
        limit = self._allowance() or 0
        extra = " (1 reserved for walls)" if self.wall_enabled.isChecked() else ""
        self.builders_label.setText(
            f"Builders free: {self._builders}{extra} — tick up to {limit} target(s)"
        )

    def _on_builders_updated(self, value: object) -> None:
        """Store the builder count reported by the scan."""
        if isinstance(value, int):
            self._builders = value
        self._update_builders_label()
        self._enforce_limit()
        self._apply()

    def _on_scan_clicked(self) -> None:
        """Ask the view-model to scan the four Build panel tabs."""
        self._viewmodel.scan_targets()

    def _on_upgrade_clicked(self) -> None:
        """Confirm and start the upgrade run."""
        answer = QMessageBox.question(
            self,
            "Upgrade now",
            "Upgrade the ticked targets using the free builders?\n"
            "This spends real resources.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._viewmodel.upgrade_now(execute=True)

    def _on_upgrade_started(self) -> None:
        """Lock the controls while the upgrade runner works."""
        self.upgrade_btn.setEnabled(False)
        self.upgrade_btn.setText("Upgrading…")
        self.scan_btn.setEnabled(False)

    def _on_upgrade_finished(self) -> None:
        """Restore the controls when the runner exits."""
        self.upgrade_btn.setText("Upgrade now")
        self.upgrade_btn.setEnabled(self._scan_allowed)
        self.scan_btn.setEnabled(self._scan_allowed)

    def _on_scan_started(self) -> None:
        """Lock the scan button while the panel scan is running."""
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning…")

    def _on_scan_finished(self) -> None:
        """Restore the scan button when the thread exits."""
        self.scan_btn.setEnabled(self._scan_allowed)
        self.scan_btn.setText("Scan from game")

    def set_bot_running(self, running: bool) -> None:
        """Disable scanning/upgrading while the bot drives the game."""
        self._scan_allowed = not running
        if not self._viewmodel.is_scanning:
            self.scan_btn.setEnabled(self._scan_allowed)
        if not self._viewmodel.is_upgrading:
            self.upgrade_btn.setEnabled(self._scan_allowed)
        self.scan_btn.setToolTip(
            "Stop the bot first" if running
            else "Open the in-game Build panel and scan all four tabs"
        )

    def _on_targets_scanned(self, payload: object) -> None:
        """Replace each tab's list with the scanned rows."""
        if not isinstance(payload, dict):
            return
        for tab, values in payload.items():
            category = _TAB_CATEGORIES.get(str(tab))
            if category is None:
                continue
            widget = self.priority_lists[category]
            names = [str(name) for name in (values or ())]
            self._fill_list(category, names, checked=False)
        self._apply()

    @staticmethod
    def _make_item(name: str, checked: bool) -> QListWidgetItem:
        """Create one checkable target row."""
        item = QListWidgetItem(name)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _fill_list(
        self,
        category: UpgradeCategory,
        names: list[str],
        checked: bool = True,
    ) -> None:
        """Replace one category list with *names*."""
        widget = self.priority_lists[category]
        widget.blockSignals(True)
        try:
            widget.clear()
            for name in names:
                widget.addItem(self._make_item(name, checked))
        finally:
            widget.blockSignals(False)

    def _apply(self, *_args: object) -> None:
        """Push widget values into the view-model draft."""
        if self._loading:
            return
        self._enforce_limit()
        self._update_builders_label()
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
            flag = self.priority_flags.get(category)
            self._viewmodel.set_priority(
                category,
                check.isChecked(),
                priorities,
                None if flag is None else flag.isChecked(),
            )
        self._viewmodel.set_priority_flag(
            UpgradeCategory.HERO, self.hero_priority.isChecked()
        )
        self._viewmodel.set_priority_flag(
            UpgradeCategory.RESOURCE, self.money_priority.isChecked()
        )

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
                flag = self.priority_flags.get(category)
                if flag is not None:
                    flag.setChecked(group.priority)
            self.hero_priority.setChecked(upgrades.hero.priority)
            self.money_priority.setChecked(upgrades.resource.priority)
            self._update_builders_label()
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

    def _on_status(self, message: str, kind: str = "info") -> None:
        """Display a status line."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Display an error line."""
        self.status.show_message(message, "error")
