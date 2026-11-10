# ==== COCbot/gui/app.py ====
# IMPORTANT: torch MUST be imported before PyQt5 on Windows. Loading Qt first
# makes torch's c10.dll fail to initialise, which also breaks PaddleOCR.
try:
    import torch  # noqa: F401
except Exception:
    pass

import ctypes
import os
import sys

from COCbot.gui.tabs.about_tab import build_about_tab
from COCbot.gui.tabs.army_recipe import ArmyRecipeTab
from COCbot.gui.tabs.clan_tabs import build_clan_tabs
from COCbot.gui.tabs.debug import DebugTab
from COCbot.gui.tabs.log_tab import build_logs_tab
from COCbot.gui.tabs.village_tabs import build_village_tabs

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import ssl

    import certifi

    CA = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", CA)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", CA)
except Exception:
    if os.environ.get("MYBOT_ALLOW_INSECURE_SSL") == "1":
        import ssl

        ssl._create_default_https_context = ssl._create_unverified_context

if getattr(sys, "frozen", False):
    import pyi_splash

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

import json
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*pin_memory.*")
import atexit
import socket
import traceback
import webbrowser
from pathlib import Path

from PyQt5.QtCore import (
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QIcon,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from COCbot.app import state as main
from COCbot.app.army_presets import attack_sides_for_label
from COCbot.app.bootstrap import bot_loop
from COCbot.app.controls import pause_bot, resume_bot
from COCbot.app.stats import zero_all_stats_files
from COCbot.app.updater import Updater
from COCbot.game.account.switch_config import load_switch_config
from COCbot.gui.accounts import AccountsMixin
from COCbot.gui.constants import (
    BLUESTACKS,
    LDPLAYER,
    MEMU,
    TEMPLATES_DIR,
    profiles_dir,
)
from COCbot.gui.dialogs import EmulatorSelectionDialog, LDInstancePickerDialog
from COCbot.gui.logs import LogsMixin
from COCbot.gui.services.qt_thread import QtThreadCompat
from COCbot.gui.settings_store import (
    load_settings,
    save_settings,
)
from COCbot.gui.tabs.stats import StatsTab
from COCbot.gui.theme import GLOBAL_QSS
from COCbot.gui.widgets import TimestampStream, TitleBar


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    QMessageBox.critical(
        None,
        "Fatal Error",
        "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
    )
    sys.exit(1)


sys.excepthook = handle_exception


class MainWindow(AccountsMixin, LogsMixin, QMainWindow):
    update_available = pyqtSignal(str, str)

    def _on_toggle_pause_play(self):
        if not self.paused:
            pause_bot()
            self._toggle_btn.setText("Resume")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self._toggle_btn.setObjectName("primaryBtn")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)
            if hasattr(self, "status_lbl"):
                self.status_lbl.setText("Status: Paused")
        else:
            resume_bot()
            self._toggle_btn.setText("Pause")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self._toggle_btn.setObjectName("")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)
            if hasattr(self, "status_lbl"):
                self.status_lbl.setText("Status: Working")
        self.paused = not self.paused

    def _stats_file_path(self, village_idx: int) -> Path:
        profiles = Path(profiles_dir)
        profiles.mkdir(exist_ok=True)
        return profiles / f"Stats_{village_idx}.json"

    def load_village_stats(self, village_idx: int) -> dict:
        path = self._stats_file_path(village_idx)
        if not path.exists():
            return {
                "gold": 0,
                "elixir": 0,
                "de": 0,
                "attacks": 0,
                "stars": {"0": 0, "1": 0, "2": 0, "3": 0},
            }
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {
                "gold": 0,
                "elixir": 0,
                "de": 0,
                "attacks": 0,
                "stars": {"0": 0, "1": 0, "2": 0, "3": 0},
            }

    def _refresh_stats_from_json(self):
        if not self.stats_tab.enable_stats_chk.isChecked():
            return
        idx = self.active_village_idx or 1
        on_disk = self.load_village_stats(idx)
        self.stats_tab.current_village_idx = idx
        self.stats_tab.set_stats_dict(on_disk)
        self.settings["stats"] = on_disk.copy()

    def on_update_available(self, remote_ver, download_url):
        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Information)
        dlg.setWindowTitle("Update Available")
        dlg.setText(f"A new version ({remote_ver}) is available.")
        dlg.setInformativeText("Download now?")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if dlg.exec_() == QMessageBox.Yes:
            webbrowser.open(download_url)

    def _toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_tab_changed(self, idx: int):
        if hasattr(self, "accounts_tab_index") and idx == self.accounts_tab_index:
            self._refresh_accounts(silent=True)
    def choose_emulator(self):
        if self.no_host:
            return self.host
        dlg = EmulatorSelectionDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            choice = dlg.getSelection()
            if choice == "memu":
                self.host = MEMU
                main.emulator_key = "memu"
                main.ld_index = 0
                main.ld_name = None
                port = 6200
            elif choice == "bluestacks":
                self.host = BLUESTACKS
                main.emulator_key = "bluestacks"
                main.ld_index = 0
                main.ld_name = None
                port = 6201
            elif choice == "ldplayer":
                main.emulator_key = "ldplayer"
                main.ld_index = 0
                main.ld_name = "LDPlayer"
                self.host = None
                port = 6202
            elif choice == "ldplayer_multi":
                pick = LDInstancePickerDialog(self)
                if pick.exec_() != QDialog.Accepted:
                    return None
                main.emulator_key = "ldplayer"
                main.ld_index = pick.index
                main.ld_name = pick.name
                self.host = None
                port = 6202 + pick.index
            else:
                return None
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sys.platform == "win32":
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                QMessageBox.warning(
                    self,
                    "Emulator Busy",
                    f"{choice.capitalize()} appears to be in use by another bot.\n"
                    "Please close that bot first.",
                )
                return None
            self._emu_socket = s
            atexit.register(self._emu_socket.close)
            self.no_host = True
            main.host = self.host
            return self.host
        return None

    def __init__(self):
        super().__init__()
        self.active_village_idx = None
        self.setWindowTitle("MyBot PHMOD v15.9")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.resize(480, 670)
        self.setMinimumSize(480, 670)
        self._drag_pos = None
        self._log_lines = []
        self._log_filter = "All events"
        self.host = None
        self.no_host = False
        self.active_village_idx = None
        self._worker = None
        self.settings = load_settings()
        self._switch_page_idx = 0
        self._switch_cfg = load_switch_config()
        self._loading_switch_ui = True

        central = QWidget()
        central.setObjectName("appRoot")
        central.setStyleSheet("QWidget#appRoot { background: #F2F5F3; }")
        vroot = QVBoxLayout(central)
        vroot.setContentsMargins(0, 0, 0, 0)
        vroot.setSpacing(0)
        self.setCentralWidget(central)

        # 1. Title bar — compact MyBot header (Figma: 480x40, #142C2B)
        header_bar = TitleBar(self)
        header_bar.setObjectName("titleBar")
        header_bar.setFixedHeight(40)
        header_bar.setStyleSheet("QWidget#titleBar { background: #142C2B; }")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(12, 0, 0, 0)
        header_layout.setSpacing(6)

        app_icon = QLabel()
        icon_path = os.path.join(TEMPLATES_DIR, "coc_icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                app_icon.setPixmap(
                    pix.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header_layout.addWidget(app_icon)
        header_layout.addSpacing(4)

        title_lbl = QLabel("MyBot")
        title_lbl.setObjectName("appTitle")
        title_lbl.setStyleSheet("color:#FFFFFF; font-size:16px; font-weight:600;")
        header_layout.addWidget(title_lbl)

        version_lbl = QLabel("PHMOD v15.9")
        version_lbl.setObjectName("appSub")
        version_lbl.setStyleSheet("color:#BFD3CE; font-size:10px;")
        header_layout.addWidget(version_lbl)
        header_layout.addSpacing(6)

        free_lbl = QLabel("Freeware · Open source")
        free_lbl.setObjectName("appBadge")
        free_lbl.setStyleSheet("color:#9FB8B1; font-size:10px;")
        header_layout.addWidget(free_lbl)
        header_layout.addStretch()

        btn_min = QPushButton("—")
        btn_min.setObjectName("winBtn")
        btn_min.setFixedSize(36, 40)
        btn_min.clicked.connect(self.showMinimized)

        btn_max = QPushButton("□")
        btn_max.setObjectName("winBtn")
        btn_max.setFixedSize(36, 40)
        btn_max.clicked.connect(self._toggle_maximized)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("winClose")
        btn_close.setFixedSize(36, 40)
        btn_close.clicked.connect(self.close)

        header_layout.addWidget(btn_min)
        header_layout.addWidget(btn_max)
        header_layout.addWidget(btn_close)
        vroot.addWidget(header_bar)

        # 2. Main tabs (6 tabs per Figma: Log / Village / Attack plan / Bot settings / Statistics / About)
        tabs_container = QWidget()
        tabs_layout = QHBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(12, 0, 12, 0)
        tabs_layout.setSpacing(0)
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabs")
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setElideMode(Qt.ElideNone)
        self.tab_widget.setUsesScrollButtons(False)
        tabs_layout.addWidget(self.tab_widget)
        vroot.addWidget(tabs_container, 1)

        logs_tab = build_logs_tab(self)
        gen_tab, upgrade_tab = build_village_tabs(self)

        # ===== TAB 2: Army tab =====
        self.army_tab = ArmyRecipeTab()
        self.army_tab.check_troops_chk.setChecked(
            bool(self.settings.get("check_troops", False))
        )
        self.army_tab.recipe_changed.connect(self._on_army_recipe_changed)

        # ===== TAB 3.5: Accounts / Switch Accounts =====
        self.accounts_tab = self._build_accounts_tab()

        clan_tab, cc_tab = build_clan_tabs(self)

        # ===== TAB 6: Statistics tab =====
        self.stats_tab = StatsTab(
            TEMPLATES_DIR,
            self.settings,
            parent=self,
        )
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats_from_json)
        self._stats_timer.start(5000)

        # ===== TAB 7: Debug tab (Crop Tool) =====
        self.debug_tab = DebugTab()

        # ===== Assemble the 6 top-level tabs =====
        def _scroll(widget):
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.NoFrame)
            sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            sa.viewport().setAutoFillBackground(False)
            sa.setStyleSheet(
                "QScrollArea, QScrollArea > QWidget > QWidget "
                "{ background: transparent; }")
            sa.setWidget(widget)
            return sa

        village_tabs = QTabWidget()
        village_tabs.setObjectName("subTabs")
        village_tabs.setDocumentMode(True)
        village_tabs.addTab(_scroll(gen_tab), "General")
        village_tabs.addTab(_scroll(upgrade_tab), "Upgrade")
        village_tabs.addTab(_scroll(self.accounts_tab), "Accounts")
        village_tabs.currentChanged.connect(
            lambda i: self._refresh_accounts(silent=True) if i == 2 else None)

        settings_tabs = QTabWidget()
        settings_tabs.setObjectName("subTabs")
        settings_tabs.setDocumentMode(True)
        settings_tabs.addTab(_scroll(clan_tab), "Clan Games")
        settings_tabs.addTab(_scroll(cc_tab), "Clan Capital")
        settings_tabs.addTab(_scroll(self.debug_tab), "Debug")

        about_tab = build_about_tab(self)

        self.tab_widget.addTab(logs_tab, "Log")
        self.tab_widget.addTab(village_tabs, "Village")
        self.tab_widget.addTab(_scroll(self.army_tab), "Attack plan")
        self.tab_widget.addTab(settings_tabs, "Bot settings")
        self.tab_widget.addTab(_scroll(self.stats_tab), "Statistics")
        self.tab_widget.addTab(about_tab, "About")
        self.attack_tab_index = 2
        self.accounts_tab_index = 1  # Village tab (kept for _on_tab_changed)
        self.tab_widget.setCurrentIndex(0)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self._refresh_accounts(silent=True)

        # ===== Log stream =====
        self.stream = TimestampStream()
        self.stream.new_line.connect(self._append_log)
        sys.stdout = self.stream
        sys.stderr = self.stream

        # ===== Bottom Bar (fixed, Figma 12px margins) =====
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(54)
        bottom_bar.setStyleSheet("QFrame { background: #F2F5F3; border: none; }")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12, 0, 12, 12)
        bottom_layout.setSpacing(12)

        self.start_btn = QPushButton("Start bot")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedSize(108, 42)
        self.start_btn.setCursor(Qt.PointingHandCursor)

        self._toggle_btn = QPushButton("Pause")
        self._toggle_btn.setFixedSize(88, 42)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self.paused = False
        self._toggle_btn.clicked.connect(self._on_toggle_pause_play)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setFixedSize(88, 42)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setCursor(Qt.PointingHandCursor)

        self.search_btn = QPushButton("⌕  Search mode")
        self.search_btn.setFixedSize(136, 42)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setToolTip("Mở tab Attack plan để chỉnh chế độ tìm trận.")
        self.search_btn.clicked.connect(
            lambda: self.tab_widget.setCurrentIndex(self.attack_tab_index))

        self.status_lbl = QLabel("Status: Ready")
        self.status_lbl.setVisible(False)

        bottom_layout.addWidget(self.start_btn)
        bottom_layout.addWidget(self._toggle_btn)
        bottom_layout.addWidget(self.stop_btn)
        bottom_layout.addWidget(self.search_btn)
        bottom_layout.addStretch()

        vroot.addWidget(bottom_bar)

        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn.clicked.connect(self.on_end)

        self._warned = False
        self.updater = Updater(self)
        self.updater.update_available.connect(self.on_update_available)
        QTimer.singleShot(500, self.updater.check_for_update)

    def _on_army_recipe_changed(self):
        name = self.army_tab.get_active_name()
        print(f"[ARMY] Recipe changed: {name}")

    def _toggle_wall_inputs(self, enabled: bool):
        policy = Qt.StrongFocus if enabled else Qt.NoFocus
        for w in [self.wall_gold_entry, self.wall_elixir_entry, self.wall_level_spin]:
            w.setEnabled(enabled)
            w.setFocusPolicy(policy)

    def on_start(self):
        if self._worker and self._worker.is_alive():
            return
        emu = self.choose_emulator()
        if emu is None and not getattr(main, "emulator_key", None):
            print("[INFO] Start aborted (no emulator selected).")
            return
        try:
            if emu:
                # After a stop/start cycle _emu_socket is None (closed on stop)
                # while no_host stays True, so never call .fileno() blindly.
                sock = getattr(self, "_emu_socket", None)
                owns_lock = sock is not None and sock.fileno() != -1
                if not owns_lock:
                    port_map = {MEMU: 6200, BLUESTACKS: 6201, LDPLAYER: 6202}
                    emu_key = getattr(main, "emulator_key", "") or ""
                    if emu_key in ("ldplayer", "ldplayer_multi"):
                        port = 6202 + int(getattr(main, "ld_index", 0) or 0)
                    else:
                        port = port_map.get(self.host, 6299)
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if sys.platform == "win32":
                        test_sock.setsockopt(
                            socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
                        )
                    try:
                        test_sock.bind(("127.0.0.1", port))
                    except OSError:
                        try:
                            test_sock.close()
                        except Exception:
                            pass
                        QMessageBox.warning(
                            self,
                            "Emulator Busy",
                            f"Port {port} is still in use by another bot.\n"
                            "Close the other bot or wait a few seconds, then retry.",
                        )
                        return
                    self._emu_socket = test_sock
                    atexit.register(test_sock.close)
            print(f"[INFO] Using emulator: {emu}")
            cfg = self._collect_cfg()
            save_settings(cfg)
            cfg["stats"] = {}
            main.stop_event.clear()
            self._worker = QtThreadCompat(
                target=bot_loop, args=(cfg,), parent=self
            )
            self._worker.start()
            print("[DEBUG] _worker type =", type(self._worker))
            print(
                "[DEBUG] _worker Qt isRunning =",
                getattr(self._worker, "isRunning", None),
            )
            print("[INFO] Bot started with attack:", cfg["attack"])
            self._set_inputs_enabled(False)
            for w in [
                self.wall_gold_entry,
                self.wall_elixir_entry,
                self.wall_level_spin,
            ]:
                w.setEnabled(False)
                w.setWindowOpacity(0.35)
            self.stats_tab.enable_stats_chk.setEnabled(False)
            self.clan_games_toggle.setEnabled(False)
            self.clan_capital_toggle.setEnabled(False)
            self.cc_level.setEnabled(False)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            if hasattr(self, "status_lbl"):
                self.status_lbl.setText("Status: Working")
                self.status_lbl.setStyleSheet("color: #f0b64c; padding-left: 8px;")
        except OSError:
            QMessageBox.warning(
                self,
                "Emulator Busy",
                "The emulator you are trying to access is being used by another bot.\n\n"
                "Close that bot and press Start again, or restart this bot and choose a different COCbot.emulator.",
            )
            print("[INFO] Start aborted (emulator in use).")
            return
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Startup Error",
                f"An unexpected error occurred when starting:\n\n{e}",
            )

    def on_end(self):
        print("[STOP] Đang dừng bot...")
        main.stop_event.set()
        main.pause_event.set()

        if getattr(self, "_worker", None) is not None:
            print("[STOP] Đang chờ worker dừng...")
            if hasattr(self._worker, "quit"):
                self._worker.quit()
            if hasattr(self._worker, "wait"):
                if not self._worker.wait(6000):
                    print("[STOP] ⚠️ Worker không chịu dừng, ép buộc terminate!")
                    self._worker.terminate()
                    self._worker.wait(1000)
            self._worker = None
            print("[STOP] Worker đã dừng.")

        wallOn = self.upgrade_chk.isChecked()
        for w in [self.wall_gold_entry, self.wall_elixir_entry, self.wall_level_spin]:
            w.setEnabled(wallOn)
            w.setWindowOpacity(1.0 if wallOn else 0.35)

        self.clan_games_toggle.setEnabled(True)
        self.clan_capital_toggle.setEnabled(True)
        self.cc_level.setEnabled(self.clan_capital_toggle.isChecked())
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stats_tab.enable_stats_chk.setEnabled(True)

        if self.paused:
            self.paused = False
            self._toggle_btn.setText("Pause")
            self._toggle_btn.setObjectName("")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)

        if hasattr(self, "status_lbl"):
            self.status_lbl.setText("Status: Ready")

        if hasattr(self, "_emu_socket") and self._emu_socket is not None:
            try:
                self._emu_socket.close()
                self._emu_socket = None
            except Exception:
                pass
        print("[STOP] Bot đã dừng hoàn toàn.")

    def _set_inputs_enabled(self, en: bool):
        for w in [
            self.gold_entry,
            self.elixir_entry,
            self.dark_entry,
            self.upgrade_chk,
            self.wall_gold_entry,
            self.wall_elixir_entry,
        ]:
            w.setEnabled(en)

    def _collect_cfg(self):
        attack_type = "Dragon_Attack"

        cfg = {
            "gold_threshold": int(self.gold_entry.text()),
            "elixir_threshold": int(self.elixir_entry.text()),
            "dark_elixir_threshold": int(self.dark_entry.text()),
            "upgrade_wall": self.upgrade_chk.isChecked(),
            "wall_level": int(self.wall_level_spin.value()),
            "wall_gold_threshold": int(self.wall_gold_entry.text()),
            "wall_elixir_threshold": int(self.wall_elixir_entry.text()),
            "upgrade_hero": self.upgrade_hero_chk.isChecked(),
            "hero_priorities": [
                name for name, cb in self.hero_checks.items()
                if cb.isChecked()
            ],
            "upgrade_defense": self.upgrade_defense_chk.isChecked(),
            "defense_priorities": [
                name for name, cb in self.defense_checks.items()
                if cb.isChecked()
            ],
            "upgrade_army": self.upgrade_army_chk.isChecked(),
            "army_priorities": [
                name for name, cb in self.army_checks.items()
                if cb.isChecked()
            ],
            "upgrade_resource": self.upgrade_resource_chk.isChecked(),
            "resource_priorities": [
                name for name, cb in self.resource_checks.items()
                if cb.isChecked()
            ],
            "upgrade_other": self.upgrade_other_chk.isChecked(),
            "other_buildings": [
                item.strip()
                for item in self.other_buildings_entry.text().split(",")
                if item.strip()
            ],
            "request_troops": self.req_chk.isChecked(),
            "attack": attack_type,
            "recipe_name": self.army_tab.get_active_name(),
            "recipe": self.army_tab.get_active_recipe(),
            "attack_side": self.army_tab.get_attack_side(),
            "check_troops": self.army_tab.get_check_troops(),
            "train_mode": "smart",
            "quick_slot": 1,
            "enable_clan_games": self.clan_games_toggle.isChecked(),
            "enable_clan_capital": self.clan_capital_toggle.isChecked(),
            "capital_hall_level": int(self.cc_level.value()),
            "enable_stats": self.stats_tab.enable_stats_chk.isChecked(),
        }

        # Preserve the redline/YOLO and dataset-capture options from settings.json.
        # _collect_cfg rebuilds the dict from widgets, so without this merge the
        # attack pipeline would never see redline_model or auto_capture_*.
        settings = getattr(self, "settings", {}) or {}
        cfg.update({
            "redline_model": settings.get("redline_model", "models/redline_seg.pt"),
            "redline_offset_ratio": float(settings.get("redline_offset_ratio", 0.35)),
            "auto_capture_dataset": bool(settings.get("auto_capture_dataset", True)),
            "auto_capture_dir": settings.get(
                "auto_capture_dir", "datasets/redline/images/raw"),
            "auto_capture_min_interval_sec": float(
                settings.get("auto_capture_min_interval_sec", 2.0)),
            "auto_capture_max_files": int(
                settings.get("auto_capture_max_files", 2000)),
            "auto_capture_only_on_fallback": bool(
                settings.get("auto_capture_only_on_fallback", True)),
            "auto_capture_success_sample": float(
                settings.get("auto_capture_success_sample", 0.1)),
            "auto_capture_scout_sample": float(
                settings.get("auto_capture_scout_sample", 1.0)),
            "auto_capture_on_scout": bool(
                settings.get("auto_capture_on_scout", True)),
            "auto_capture_on_attack": bool(
                settings.get("auto_capture_on_attack", False)),
            "auto_capture_format": str(
                settings.get("auto_capture_format", "jpg")),
            "auto_capture_jpeg_quality": int(
                settings.get("auto_capture_jpeg_quality", 92)),
            "auto_capture_webp_quality": int(
                settings.get("auto_capture_webp_quality", 90)),
            "auto_capture_png_compression": int(
                settings.get("auto_capture_png_compression", 9)),
        })
        cfg["attack_sides"] = attack_sides_for_label(cfg["attack_side"])
        return cfg

    def closeEvent(self, event):
        print("\n[SHUTDOWN] Closing application...")

        try:
            if hasattr(self, "stream"):
                self.stream.new_line.disconnect(self._append_log)
        except Exception:
            pass

        try:
            save_settings(self._collect_cfg())
        except Exception as e:
            print(f"[SHUTDOWN] could not save settings: {e}")

        try:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
        except Exception:
            pass

        if hasattr(self, "_stats_timer") and self._stats_timer is not None:
            try:
                self._stats_timer.stop()
            except Exception:
                pass

        if getattr(self, "_worker", None) is not None:
            print("[SHUTDOWN] Đang gửi tín hiệu dừng tới worker...")
            main.stop_event.set()
            main.pause_event.set()

            if hasattr(self._worker, "quit"):
                self._worker.quit()

            if hasattr(self._worker, "wait"):
                if not self._worker.wait(5000):
                    print("[SHUTDOWN] ⚠️ Worker không chịu dừng, ép buộc terminate!")
                    self._worker.terminate()
                    self._worker.wait(2000)

            self._worker = None
            print("[SHUTDOWN] Worker đã dừng.")

        if hasattr(self, "_emu_socket") and self._emu_socket is not None:
            try:
                self._emu_socket.close()
                self._emu_socket = None
            except Exception:
                pass

        super().closeEvent(event)
        QApplication.quit()


def main_gui():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_QSS)
    zero_all_stats_files()
    icon_path = os.path.join(TEMPLATES_DIR, "coc_icon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(TEMPLATES_DIR, "app_icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    win = MainWindow()
    win.setWindowIcon(QIcon(icon_path))
    win.show()
    if getattr(sys, "frozen", False):
        pyi_splash.close()
    sys.exit(app.exec_())


if __name__ == "__main__":
    try:
        main_gui()
    except Exception:
        traceback.print_exc()
        QMessageBox.critical(
            None,
            "Startup Error",
            "An error occurred before the UI could start.\n\n" + traceback.format_exc(),
        )
