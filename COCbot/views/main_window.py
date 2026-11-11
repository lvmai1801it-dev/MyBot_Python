"""Shell main window: header, tabs, and run controls."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from COCbot.core.config.paths import get_project_paths
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import LogLevel
from COCbot.ui_components import (
    DangerButton,
    PrimaryButton,
    SecondaryButton,
    StatusLabel,
    TitleBar,
)
from COCbot.viewmodels.main_viewmodel import MainViewModel

_LEVEL_KIND = {
    LogLevel.DEBUG: "info",
    LogLevel.INFO: "info",
    LogLevel.SUCCESS: "success",
    LogLevel.WARNING: "warning",
    LogLevel.ERROR: "error",
    LogLevel.CRITICAL: "error",
}


class MainWindow(QMainWindow):
    """Compose the migrated feature views around a shared main view-model."""

    def __init__(
        self,
        logs_view: QWidget,
        settings_view: QWidget,
        accounts_view: QWidget,
        attack_view: QWidget,
        statistics_view: QWidget,
        viewmodel: MainViewModel,
        parent: QWidget | None = None,
    ) -> None:
        """Build the shell and connect view-model signals."""
        super().__init__(parent)
        self._viewmodel = viewmodel
        self._paused = False
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(560, 760)
        self.setWindowTitle("MyBot PHMOD")

        central = QWidget()
        central.setObjectName("appRoot")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        root.addWidget(self._build_header())
        root.addWidget(
            self._build_tabs(
                logs_view,
                settings_view,
                accounts_view,
                attack_view,
                statistics_view,
            ),
            1,
        )
        root.addWidget(self._build_footer())

        self._viewmodel.running_changed.connect(self._on_running_changed)
        self._viewmodel.status_message.connect(self._on_status)
        self._viewmodel.error_occurred.connect(self._on_error)
        self._viewmodel.event_emitted.connect(self._on_event)

    def _build_header(self) -> QWidget:
        """Create the draggable header with window buttons."""
        header = TitleBar(self)
        header.setObjectName("appHeader")
        header.setFixedHeight(44)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)

        icon_path = get_project_paths().templates_dir / "coc_icon.png"
        icon = QLabel()
        if icon_path.is_file():
            pixmap = QIcon(str(icon_path)).pixmap(18, 18)
            icon.setPixmap(pixmap)
        layout.addWidget(icon)

        title = QLabel("MyBot")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        subtitle = QLabel("MVVM shell")
        subtitle.setObjectName("appSub")
        layout.addWidget(subtitle)
        layout.addStretch(1)

        self.host_label = QLabel("ADB: ready")
        self.host_label.setObjectName("appBadge")
        layout.addWidget(self.host_label)

        minimize = QPushButton("—")
        minimize.setObjectName("winBtn")
        minimize.setFixedSize(36, 44)
        minimize.clicked.connect(self.showMinimized)
        close = QPushButton("✕")
        close.setObjectName("winClose")
        close.setFixedSize(36, 44)
        close.clicked.connect(self.close)
        layout.addWidget(minimize)
        layout.addWidget(close)
        return header

    def _build_tabs(
        self,
        logs_view: QWidget,
        settings_view: QWidget,
        accounts_view: QWidget,
        attack_view: QWidget,
        statistics_view: QWidget,
    ) -> QTabWidget:
        """Create the top-level feature tabs."""
        tabs = QTabWidget()
        tabs.setObjectName("mainTabs")
        tabs.setDocumentMode(True)
        tabs.addTab(logs_view, "Logs")
        tabs.addTab(settings_view, "Settings")
        tabs.addTab(accounts_view, "Accounts")
        tabs.addTab(attack_view, "Attack")
        tabs.addTab(statistics_view, "Statistics")
        return tabs

    def _build_footer(self) -> QWidget:
        """Create the status line and run controls."""
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(8)
        self.status = StatusLabel()
        layout.addWidget(self.status, 1)

        self.start_btn = PrimaryButton("Start bot")
        self.pause_btn = SecondaryButton("Pause")
        self.stop_btn = DangerButton("Stop")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._viewmodel.start)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.stop_btn.clicked.connect(self._viewmodel.stop)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        return footer

    def _on_pause_clicked(self) -> None:
        """Toggle pause/resume through the view-model."""
        if self._paused:
            self._viewmodel.resume()
            self.pause_btn.setText("Pause")
            self._paused = False
        else:
            self._viewmodel.pause()
            self.pause_btn.setText("Resume")
            self._paused = True

    def _on_running_changed(self, running: bool) -> None:
        """Enable controls according to the worker state."""
        self.start_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.stop_btn.setEnabled(running)
        if not running:
            self.pause_btn.setText("Pause")
            self._paused = False

    def _on_status(self, message: str, kind: str) -> None:
        """Display a shell status line."""
        self.status.show_message(message, kind)

    def _on_error(self, message: str) -> None:
        """Display a shell error."""
        self.status.show_message(message, "error")

    def _on_event(self, event: object) -> None:
        """Display one engine event."""
        if not isinstance(event, BotEvent):
            return
        self.status.show_message(event.message, _LEVEL_KIND.get(event.level, "info"))

    def _toggle_maximized(self) -> None:
        """Toggle maximize for double-click on the header."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def closeEvent(self, event) -> None:
        """Stop the worker before closing the window."""
        self._viewmodel.shutdown()
        super().closeEvent(event)
