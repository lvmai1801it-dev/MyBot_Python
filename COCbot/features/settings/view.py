"""Settings feature view (layout + signal binding only)."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from COCbot.core.config.defaults import EMULATOR_HOSTS
from COCbot.core.config.schema import AppConfig
from COCbot.features.settings.model import (
    ATTACK_CHOICES,
    EMULATOR_CHOICES,
    LOG_LEVEL_CHOICES,
    SIDE_CHOICES,
)
from COCbot.features.settings.viewmodel import SettingsViewModel
from COCbot.models.enums import EmulatorType
from COCbot.ui_components import (
    Card,
    PrimaryButton,
    SecondaryButton,
    StatusLabel,
)


class SettingsView(QWidget):
    """Render the settings draft and forward user intent to the view-model."""

    def __init__(self, viewmodel: SettingsViewModel, parent: QWidget | None = None) -> None:
        """Build the layout and bind view-model signals."""
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

    # ------------------------------------------------------------------ layout
    def _build_ui(self) -> None:
        """Create every widget; no business logic lives here."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(10)

        layout.addWidget(self._build_loot_card())
        layout.addWidget(self._build_wall_card())
        layout.addWidget(self._build_attack_card())
        layout.addWidget(self._build_clan_card())
        layout.addWidget(self._build_emulator_card())
        layout.addWidget(self._build_logging_card())
        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addLayout(self._build_footer())

    def _build_loot_card(self) -> Card:
        """Build the loot-threshold card."""
        card = Card(
            "Loot thresholds",
            "Skip a base when its available loot is below these values.",
        )
        self.gold_spin = self._spin(0, 100_000_000, 1_000)
        self.elixir_spin = self._spin(0, 100_000_000, 1_000)
        self.dark_spin = self._spin(0, 1_000_000, 100)
        card.add_row("Gold", self.gold_spin)
        card.add_row("Elixir", self.elixir_spin)
        card.add_row("Dark elixir", self.dark_spin)
        return card

    def _build_wall_card(self) -> Card:
        """Build the wall-upgrade card."""
        card = Card("Wall upgrade", "Automatically spend overflow loot on walls.")
        self.wall_enabled = QCheckBox("Enable wall upgrade")
        self.wall_level = self._spin(1, 20, 1)
        self.wall_gold = self._spin(0, 100_000_000, 100_000)
        self.wall_elixir = self._spin(0, 100_000_000, 100_000)
        card.add(self.wall_enabled)
        card.add_row("Target level", self.wall_level)
        card.add_row("Gold threshold", self.wall_gold)
        card.add_row("Elixir threshold", self.wall_elixir)
        return card

    def _build_attack_card(self) -> Card:
        """Build the default attack card."""
        card = Card("Attack defaults", "Strategy and preferred deployment side.")
        self.attack_combo = self._combo(ATTACK_CHOICES)
        self.side_combo = self._combo(SIDE_CHOICES)
        card.add_row("Strategy", self.attack_combo)
        card.add_row("Side", self.side_combo)
        return card

    def _build_clan_card(self) -> Card:
        """Build the clan automation card."""
        card = Card("Clan", "Clan Games, Clan Capital, and troop requests.")
        self.clan_games = QCheckBox("Enable Clan Games")
        self.clan_capital = QCheckBox("Enable Clan Capital")
        self.capital_level = self._spin(1, 15, 1)
        self.request_troops = QCheckBox("Request troops")
        card.add(self.clan_games)
        card.add(self.clan_capital)
        card.add_row("Capital hall level", self.capital_level)
        card.add(self.request_troops)
        return card

    def _build_emulator_card(self) -> Card:
        """Build the emulator/ADB card."""
        card = Card("Emulator", "Select the emulator family and ADB host.")
        self.emulator_combo = QComboBox()
        for kind in EMULATOR_CHOICES:
            self.emulator_combo.addItem(kind.value.capitalize(), kind)
        self.emulator_combo.setMinimumWidth(160)
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("127.0.0.1:5555")
        self.stats_check = QCheckBox("Enable statistics")
        card.add_row("Emulator", self.emulator_combo)
        card.add_row("ADB host", self.host_edit)
        card.add(self.stats_check)
        return card

    def _build_logging_card(self) -> Card:
        """Build the logging card."""
        card = Card("Logging", "Console/file verbosity for the bot log.")
        self.log_level_combo = self._combo(LOG_LEVEL_CHOICES)
        self.log_file_check = QCheckBox("Write rotating log file")
        card.add_row("Level", self.log_level_combo)
        card.add(self.log_file_check)
        return card

    def _build_footer(self) -> QHBoxLayout:
        """Build the status line and action buttons."""
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
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
        return footer

    @staticmethod
    def _spin(minimum: int, maximum: int, step: int) -> QSpinBox:
        """Create a configured spin box."""
        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setSingleStep(step)
        widget.setMinimumWidth(140)
        return widget

    @staticmethod
    def _combo(items: tuple[str, ...]) -> QComboBox:
        """Create a configured combo box."""
        widget = QComboBox()
        widget.addItems(list(items))
        widget.setMinimumWidth(160)
        return widget

    # ------------------------------------------------------------------ wiring
    def _connect_signals(self) -> None:
        """Connect widget changes to the view-model commands."""
        for spin in (
            self.gold_spin,
            self.elixir_spin,
            self.dark_spin,
            self.wall_level,
            self.wall_gold,
            self.wall_elixir,
            self.capital_level,
        ):
            spin.valueChanged.connect(self._apply)
        for toggle in (
            self.wall_enabled,
            self.clan_games,
            self.clan_capital,
            self.request_troops,
            self.stats_check,
            self.log_file_check,
        ):
            toggle.toggled.connect(self._apply)
        self.attack_combo.currentTextChanged.connect(self._apply)
        self.side_combo.currentTextChanged.connect(self._apply)
        self.log_level_combo.currentTextChanged.connect(self._apply)
        self.host_edit.textChanged.connect(self._apply)
        self.emulator_combo.currentTextChanged.connect(self._on_emulator_changed)
        self.save_btn.clicked.connect(self._viewmodel.save)
        self.reload_btn.clicked.connect(self._viewmodel.reload)
        self.defaults_btn.clicked.connect(self._on_defaults)

    def _apply(self, *_args: object) -> None:
        """Push the current widget values into the view-model draft."""
        if self._loading:
            return
        vm = self._viewmodel
        vm.set_resources(
            self.gold_spin.value(),
            self.elixir_spin.value(),
            self.dark_spin.value(),
        )
        vm.set_wall_upgrade(
            self.wall_enabled.isChecked(),
            self.wall_level.value(),
            self.wall_gold.value(),
            self.wall_elixir.value(),
        )
        vm.set_attack(self.attack_combo.currentText(), self.side_combo.currentText())
        vm.set_clan(
            self.clan_games.isChecked(),
            self.clan_capital.isChecked(),
            self.capital_level.value(),
            self.request_troops.isChecked(),
        )
        kind = self.emulator_combo.currentData()
        vm.set_emulator(kind or EmulatorType.MEMU, self.host_edit.text())
        vm.set_logging(
            self.log_level_combo.currentText(),
            self.log_file_check.isChecked(),
        )
        vm.set_stats(self.stats_check.isChecked())

    def _on_emulator_changed(self, *_args: object) -> None:
        """Fill the default host when the emulator family changes."""
        if self._loading:
            return
        kind = self.emulator_combo.currentData()
        current = self.host_edit.text().strip()
        defaults = {host for host in EMULATOR_HOSTS.values()}
        if not current or current in defaults:
            self.host_edit.setText(EMULATOR_HOSTS.get(kind, ""))
        self._apply()

    # ------------------------------------------------------------------ slots
    def _on_loaded(self, config: AppConfig) -> None:
        """Render a loaded configuration without emitting user intent."""
        self._loading = True
        try:
            self.gold_spin.setValue(config.resources.gold)
            self.elixir_spin.setValue(config.resources.elixir)
            self.dark_spin.setValue(config.resources.dark_elixir)
            self.wall_enabled.setChecked(config.upgrades.wall.enabled)
            self.wall_level.setValue(config.upgrades.wall.level)
            self.wall_gold.setValue(config.upgrades.wall.gold_threshold)
            self.wall_elixir.setValue(config.upgrades.wall.elixir_threshold)
            self._set_combo_text(self.attack_combo, config.attack.name)
            self._set_combo_text(self.side_combo, config.attack.side)
            self.clan_games.setChecked(config.clan.enable_clan_games)
            self.clan_capital.setChecked(config.clan.enable_clan_capital)
            self.capital_level.setValue(config.clan.capital_hall_level)
            self.request_troops.setChecked(config.clan.request_troops)
            self._set_emulator(config.emulator.emulator_type)
            self.host_edit.setText(config.emulator.host)
            self.stats_check.setChecked(config.enable_stats)
            self._set_combo_text(self.log_level_combo, config.logging.level)
            self.log_file_check.setChecked(config.logging.file_enabled)
        finally:
            self._loading = False
        self.save_btn.setEnabled(self._viewmodel.is_dirty)

    def _on_saved(self, config: AppConfig) -> None:
        """Disable Save after a successful write."""
        self.save_btn.setEnabled(False)

    def _on_dirty_changed(self, dirty: bool) -> None:
        """Enable Save only when the draft differs from disk."""
        self.save_btn.setEnabled(dirty)

    def _on_status(self, message: str, kind: str) -> None:
        """Display a view-model status message."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Display a view-model error."""
        self.status.show_message(message, "error")

    def _on_defaults(self) -> None:
        """Load defaults into the draft and re-render."""
        self._viewmodel.reset_defaults()
        self._on_loaded(self._viewmodel.config)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: str) -> None:
        """Select *value*, adding it when the list does not contain it."""
        index = combo.findText(value)
        if index < 0:
            combo.addItem(value)
            index = combo.count() - 1
        combo.setCurrentIndex(index)

    def _set_emulator(self, kind: EmulatorType) -> None:
        """Select the emulator family stored in the config."""
        index = self.emulator_combo.findData(kind)
        if index >= 0:
            self.emulator_combo.setCurrentIndex(index)
