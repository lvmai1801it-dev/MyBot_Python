"""Attack feature view (layout + signal binding only)."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from COCbot.features.attack.model import AttackScan
from COCbot.features.attack.viewmodel import AttackViewModel
from COCbot.ui_components import (
    Card,
    DangerButton,
    PrimaryButton,
    SecondaryButton,
    StatusLabel,
)


class AttackView(QWidget):
    """Render attack scans and forward user actions to the view-model."""

    def __init__(self, viewmodel: AttackViewModel, parent: QWidget | None = None) -> None:
        """Build the attack panel and bind view-model signals."""
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        """Create the cards, progress bar, and live log."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        scan_card = Card("Attack scan", "Capture the enemy base and build a deploy plan.")
        self.status = StatusLabel()
        scan_card.add(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 4)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        scan_card.add(self.progress)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.scan_btn = PrimaryButton("Scan base")
        self.stop_btn = DangerButton("Stop")
        self.stop_btn.setEnabled(False)
        self.deploy_btn = SecondaryButton("Dry-run deploy")
        self.deploy_btn.setEnabled(False)
        buttons.addWidget(self.scan_btn)
        buttons.addWidget(self.stop_btn)
        buttons.addWidget(self.deploy_btn)
        buttons.addStretch(1)
        scan_card.add_layout(buttons)
        layout.addWidget(scan_card)

        plan_card = Card("Current plan", "Detected target, redline source, and troop recipe.")
        self.target_label = QLabel("No scan yet")
        self.target_label.setObjectName("cardTitle")
        self.detail_label = QLabel("—")
        self.detail_label.setObjectName("muted")
        self.detail_label.setWordWrap(True)
        self.troops_label = QLabel("—")
        self.troops_label.setObjectName("muted")
        self.troops_label.setWordWrap(True)
        plan_card.add(self.target_label)
        plan_card.add(self.detail_label)
        plan_card.add(self.troops_label)
        layout.addWidget(plan_card)

        log_card = Card("Scan log", "Live progress from the background worker.")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        log_card.add(self.log_view)
        layout.addWidget(log_card)
        layout.addStretch(1)

    def _connect_signals(self) -> None:
        """Connect buttons and view-model signals."""
        self.scan_btn.clicked.connect(self._viewmodel.scan)
        self.stop_btn.clicked.connect(self._viewmodel.cancel)
        self.deploy_btn.clicked.connect(self._on_deploy)
        self._viewmodel.plan_ready.connect(self._on_plan_ready)
        self._viewmodel.deployed.connect(self._on_deployed)
        self._viewmodel.progress.connect(self._on_progress)
        self._viewmodel.status_message.connect(self._on_status)
        self._viewmodel.error_occurred.connect(self._on_error)
        self._viewmodel.busy_changed.connect(self._on_busy_changed)

    def _append_log(self, message: str) -> None:
        """Append one line to the read-only log."""
        self.log_view.appendPlainText(message)

    def _on_deploy(self) -> None:
        """Request a safe dry-run deployment."""
        self._viewmodel.deploy_current(dry_run=True)

    def _on_plan_ready(self, scan: object) -> None:
        """Render a completed scan."""
        if not isinstance(scan, AttackScan):
            return
        target = scan.plan.target
        if target is None:
            self.target_label.setText("No target detected")
            self.detail_label.setText(f"Redline: {scan.source} · no recommendation")
            self.deploy_btn.setEnabled(False)
            self._append_log("No target detected")
            return
        self.target_label.setText(f"{target.label} · {target.confidence:.2f}")
        self.detail_label.setText(
            f"Side {scan.plan.side} · redline {scan.source} · "
            f"{len(scan.redline.edges)} edges · {scan.duration:.2f}s"
        )
        recipe = []
        if scan.plan.troops:
            recipe.append("troops " + ", ".join(f"{k}×{v}" for k, v in scan.plan.troops.items()))
        if scan.plan.spells:
            recipe.append("spells " + ", ".join(f"{k}×{v}" for k, v in scan.plan.spells.items()))
        if scan.plan.siege:
            recipe.append("siege " + ", ".join(f"{k}×{v}" for k, v in scan.plan.siege.items()))
        self.troops_label.setText(" · ".join(recipe) if recipe else "No recipe configured")
        self.deploy_btn.setEnabled(scan.redline.is_valid())
        self._append_log(
            f"Plan: {target.label} conf={target.confidence:.2f} "
            f"side={scan.plan.side} source={scan.source}"
        )

    def _on_deployed(self, taps: int) -> None:
        """Log the deployment result."""
        self._append_log(f"Deployment finished: {taps} taps")

    def _on_progress(self, current: int, total: int, message: str) -> None:
        """Update the progress bar from worker progress."""
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(current)
        self.progress.setFormat(f"{message} %p%")
        self._append_log(message)

    def _on_status(self, message: str, kind: str) -> None:
        """Show a status line."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Show an error line and log it."""
        self.status.show_message(message, "error")
        self._append_log(f"ERROR: {message}")

    def _on_busy_changed(self, busy: bool) -> None:
        """Toggle buttons while a worker is running."""
        self.scan_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)
        if busy:
            self.progress.setValue(0)
            self.progress.setFormat("Working… %p%")
