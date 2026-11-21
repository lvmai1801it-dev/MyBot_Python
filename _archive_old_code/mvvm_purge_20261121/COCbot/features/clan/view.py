"""Clan feature view: Clan Games, Clan Capital, and donation settings."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from COCbot.core.config.schema import ClanConfig
from COCbot.features.clan.viewmodel import ClanViewModel
from COCbot.ui_components import Card, PrimaryButton, SecondaryButton, StatusLabel


class ClanView(QWidget):
    """Edit the clan automation toggles; no game logic lives here."""

    def __init__(self, viewmodel: ClanViewModel, parent: QWidget | None = None) -> None:
        """Build the clan panel and bind view-model signals."""
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
        """Create the Clan Games, Capital, and donation cards."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        games_card = Card("Clan Games", "Play Clan Games events when enabled.")
        self.games_check = QCheckBox("Enable Clan Games")
        games_card.add(self.games_check)
        layout.addWidget(games_card)

        capital_card = Card("Clan Capital", "Attack Capital districts when enabled.")
        self.capital_check = QCheckBox("Enable Clan Capital")
        self.capital_level = QSpinBox()
        self.capital_level.setRange(1, 15)
        self.capital_level.setMinimumWidth(120)
        capital_card.add(self.capital_check)
        capital_card.add_row("Capital hall level", self.capital_level)
        layout.addWidget(capital_card)

        donate_card = Card("Donations", "Request troops from clan members.")
        self.request_check = QCheckBox("Request troops")
        donate_card.add(self.request_check)
        layout.addWidget(donate_card)
        layout.addStretch(1)

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

    def _connect_signals(self) -> None:
        """Connect widgets to the bulk-apply handler."""
        self.games_check.toggled.connect(self._apply)
        self.capital_check.toggled.connect(self._apply)
        self.capital_level.valueChanged.connect(self._apply)
        self.request_check.toggled.connect(self._apply)
        self.save_btn.clicked.connect(self._viewmodel.save)
        self.reload_btn.clicked.connect(self._viewmodel.load)
        self.defaults_btn.clicked.connect(self._on_defaults)

    def _apply(self, *_args: object) -> None:
        """Push widget values into the view-model draft."""
        if self._loading:
            return
        self._viewmodel.set_options(
            self.games_check.isChecked(),
            self.capital_check.isChecked(),
            self.capital_level.value(),
            self.request_check.isChecked(),
        )

    def _on_loaded(self, config: object) -> None:
        """Render a loaded clan configuration."""
        if not isinstance(config, ClanConfig):
            return
        self._loading = True
        try:
            self.games_check.setChecked(config.enable_clan_games)
            self.capital_check.setChecked(config.enable_clan_capital)
            self.capital_level.setValue(config.capital_hall_level)
            self.request_check.setChecked(config.request_troops)
        finally:
            self._loading = False
        self.save_btn.setEnabled(self._viewmodel.is_dirty)

    def _on_saved(self, config: object) -> None:
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
