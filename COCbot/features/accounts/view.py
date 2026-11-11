"""Accounts feature view (layout + signal binding only)."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from COCbot.features.accounts.viewmodel import AccountsViewModel
from COCbot.models.account import AccountsSnapshot
from COCbot.ui_components import (
    Card,
    DangerButton,
    PrimaryButton,
    SecondaryButton,
    StatusLabel,
)


class AccountsView(QWidget):
    """Render shared_prefs profiles and forward actions to the view-model."""

    def __init__(self, viewmodel: AccountsViewModel, parent: QWidget | None = None) -> None:
        """Build the accounts panel and bind view-model signals."""
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._current_profile = ""
        self._build_ui()
        self._connect_signals()
        self._viewmodel.refresh()

    def _build_ui(self) -> None:
        """Create profile, auto-switch, and action widgets."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        profile_card = Card(
            "shared_prefs profiles",
            "Pull saves the current account. Push/Switch restores a stored profile.",
        )
        self.root_label = QLabel("ADB root: checking…")
        self.root_label.setObjectName("muted")
        self.current_label = QLabel("Current profile: —")
        self.current_label.setObjectName("muted")
        profile_card.add(self.root_label)
        profile_card.add(self.current_label)

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(260)
        profile_card.add(self.profile_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("New profile name for Pull")
        profile_card.add(self.name_edit)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.refresh_btn = SecondaryButton("Refresh")
        self.pull_btn = PrimaryButton("Pull current")
        self.push_btn = SecondaryButton("Push")
        self.switch_btn = SecondaryButton("Switch")
        self.delete_btn = DangerButton("Delete")
        buttons.addWidget(self.refresh_btn)
        buttons.addWidget(self.pull_btn)
        buttons.addWidget(self.push_btn)
        buttons.addWidget(self.switch_btn)
        buttons.addWidget(self.delete_btn)
        buttons.addStretch(1)
        profile_card.add_layout(buttons)
        layout.addWidget(profile_card)

        auto_card = Card(
            "Auto switch",
            "Rotate accounts after a fixed number of attacks.",
        )
        self.auto_enabled = QCheckBox("Enable auto-switch")
        self.attacks_spin = QSpinBox()
        self.attacks_spin.setRange(1, 99)
        self.attacks_spin.setMinimumWidth(100)
        self.save_auto_btn = SecondaryButton("Save auto-switch")
        auto_row = QHBoxLayout()
        auto_row.addWidget(self.auto_enabled)
        auto_row.addStretch(1)
        auto_row.addWidget(QLabel("Attacks per account"))
        auto_row.addWidget(self.attacks_spin)
        auto_row.addWidget(self.save_auto_btn)
        auto_card.add_layout(auto_row)
        layout.addWidget(auto_card)

        self.status = StatusLabel()
        layout.addWidget(self.status)
        layout.addStretch(1)

    def _connect_signals(self) -> None:
        """Connect buttons and view-model signals."""
        self.refresh_btn.clicked.connect(self._viewmodel.refresh)
        self.pull_btn.clicked.connect(self._on_pull)
        self.push_btn.clicked.connect(self._on_push)
        self.switch_btn.clicked.connect(self._on_switch)
        self.delete_btn.clicked.connect(self._on_delete)
        self.save_auto_btn.clicked.connect(self._on_save_auto)
        self._viewmodel.snapshot_loaded.connect(self._on_snapshot)
        self._viewmodel.action_finished.connect(self._on_action_finished)
        self._viewmodel.status_message.connect(self._on_status)
        self._viewmodel.error_occurred.connect(self._on_error)
        self._viewmodel.busy_changed.connect(self._on_busy_changed)

    def selected_profile(self) -> str:
        """Return the profile name selected in the combo box."""
        data = self.profile_combo.currentData()
        return str(data or "").strip()

    def _on_snapshot(self, snapshot: object) -> None:
        """Populate widgets from a fresh snapshot."""
        if not isinstance(snapshot, AccountsSnapshot):
            return
        selected = self.selected_profile()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in snapshot.profiles:
            self.profile_combo.addItem(profile.display_text(), profile.name)
        if selected:
            index = self.profile_combo.findData(selected)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)

        self._current_profile = snapshot.current_profile
        self.current_label.setText(f"Current profile: {snapshot.current_profile or '—'}")
        self.root_label.setText(f"ADB: {snapshot.root_label}")
        self.auto_enabled.setChecked(bool(snapshot.config.get("enabled", False)))
        self.attacks_spin.setValue(int(snapshot.config.get("consecutive_attacks", 2) or 2))
        if snapshot.profiles:
            self.status.show_message("Profiles loaded", "info")
        else:
            self.status.show_message("No shared_prefs profiles found", "warning")

    def _on_pull(self) -> None:
        """Pull the current account into the typed/selected name."""
        name = self.name_edit.text().strip() or self.selected_profile()
        if not name:
            self.status.show_message("Enter a profile name before Pull", "warning")
            return
        self._viewmodel.pull(name)

    def _on_push(self) -> None:
        """Push the selected profile into the game."""
        name = self.selected_profile()
        if not name:
            self.status.show_message("Select a profile before Push", "warning")
            return
        self._viewmodel.push(name, self._current_profile)

    def _on_switch(self) -> None:
        """Switch to the selected profile."""
        name = self.selected_profile()
        if not name:
            self.status.show_message("Select a profile before Switch", "warning")
            return
        self._viewmodel.switch(name, self._current_profile)

    def _on_delete(self) -> None:
        """Delete the selected profile after confirmation."""
        name = self.selected_profile()
        if not name:
            self.status.show_message("Select a profile before Delete", "warning")
            return
        answer = QMessageBox.question(
            self,
            "Delete profile",
            f"Delete shared_prefs profile '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._viewmodel.delete(name)

    def _on_save_auto(self) -> None:
        """Persist the auto-switch options."""
        self._viewmodel.save_auto_switch(
            self.auto_enabled.isChecked(),
            self.attacks_spin.value(),
        )

    def _on_action_finished(self, action: str) -> None:
        """Refresh the list after a profile mutation."""
        if action != "Refresh":
            self._viewmodel.refresh()

    def _on_status(self, message: str, kind: str) -> None:
        """Show a status line."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Show an error line."""
        self.status.show_message(message, "error")

    def _on_busy_changed(self, busy: bool) -> None:
        """Disable all action buttons while a worker runs."""
        for button in (
            self.refresh_btn,
            self.pull_btn,
            self.push_btn,
            self.switch_btn,
            self.delete_btn,
            self.save_auto_btn,
        ):
            button.setEnabled(not busy)
