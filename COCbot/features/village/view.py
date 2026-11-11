"""Village / upgrade feature view (config-only for non-wall groups)."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
        for category in PRIORITY_CATEGORIES:
            self.tabs.addTab(self._build_priority_tab(category), _CATEGORY_LABELS[category])
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.status = StatusLabel()
        footer.addWidget(self.status, 1)
        self.defaults_btn = SecondaryButton("Defaults")
        self.reload_btn = SecondaryButton("Reload")
        self.save_btn = PrimaryButton("Save")
        self.save_btn.setEnabled(False)
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
        """Create a config-only priority list tab."""
        card = Card(
            f"{_CATEGORY_LABELS[category]} upgrades",
            "Configuration only in this build; the bot uses the list when enabled.",
        )
        check = QCheckBox(f"Enable {_CATEGORY_LABELS[category].lower()} upgrades")
        edit = QLineEdit()
        edit.setPlaceholderText("Comma-separated priorities, e.g. Queen, King")
        card.add(check)
        card.add_row("Priority list", edit)
        self.priority_checks[category] = check
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
        self.save_btn.clicked.connect(self._viewmodel.save)
        self.reload_btn.clicked.connect(self._viewmodel.load)
        self.defaults_btn.clicked.connect(self._on_defaults)

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
            text = self.priority_edits[category].text()
            priorities = [item.strip() for item in text.split(",") if item.strip()]
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
                self.priority_edits[category].setText(", ".join(group.priorities))
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
