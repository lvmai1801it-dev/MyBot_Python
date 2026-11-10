# ==== COCbot/gui/app.py ====
# IMPORTANT: torch MUST be imported before PyQt5 on Windows. Loading Qt first
# makes torch's c10.dll fail to initialise, which also breaks PaddleOCR.
try:
    import torch  # noqa: F401
except Exception:
    pass

import ctypes
import os
import re
import sys

import COCbot.app.paths

from COCbot.gui.tabs.army_recipe import ArmyRecipeTab
from COCbot.gui.tabs.debug import DebugTab

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
app = QApplication(sys.argv)

import json
import logging
import tempfile
import threading
import time
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*pin_memory.*")
import atexit
import socket
import traceback
import webbrowser
from pathlib import Path

from PyQt5.QtCore import (
    QObject,
    QSize,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPixmap,
    QTextCursor,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from COCbot.app.updater import Updater

from COCbot.app import state as main
from COCbot.app.bootstrap import bot_loop
from COCbot.emulator.ldplayer import list_ld_instances
from COCbot.game.account.shared_prefs import SharedPrefsManager, SharedPrefsError
from COCbot.game.account.switch_config import (
    ACCOUNTS_PER_PAGE,
    MAX_ACCOUNTS,
    load_switch_config,
    save_switch_config,
)
from COCbot.gui.services.qt_thread import QtThreadCompat
from COCbot.gui.tabs.stats import StatsTab
from COCbot.gui.theme import GLOBAL_QSS
from COCbot.app.controls import pause_bot, resume_bot
from COCbot.app.army_presets import attack_sides_for_label
from COCbot.app.stats import  zero_all_stats_files

BASE_DIR = str(COCbot.app.paths.SRC_DIR)
APP_DIR = BASE_DIR
ATTACK_DIR = str(COCbot.app.paths.ATTACKS_DIR)
BG = str(COCbot.app.paths.TEMPLATE_DIR)
TEMPLATES_DIR = BG
CFG_PATH = str(COCbot.app.paths.SETTINGS_JSON)
profiles_dir = str(COCbot.app.paths.PROFILES_DIR)

MEMU = "127.0.0.1:21503"
BLUESTACKS = "127.0.0.1:5556"
LDPLAYER = "127.0.0.1:5555"


class EmulatorSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = None
        self.setWindowTitle("Select Emulator")
        self.setModal(True)
        self.setFixedSize(720, 260)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #F2F5F3;
                border: 1px solid #DCE5E1;
                border-radius: 12px;
            }
            """
        )
        header = QLabel("CHOOSE YOUR EMULATOR", self)
        header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        header.setStyleSheet("color:#193431; letter-spacing: 1px;")
        header.setAlignment(Qt.AlignCenter)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(20, 20, 20, 8)
        hbox.setSpacing(28)

        def make_button(name, img_path):
            btn = QToolButton(self)
            btn.setIcon(QIcon(img_path))
            btn.setIconSize(QSize(80, 80))
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setText(name)
            btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
            btn.setMinimumWidth(170)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QToolButton { color:#193431; background:transparent; border:none; }"
                "QToolButton:hover { color:#13775F; }"
            )
            return btn

        memu_logo = os.path.join(TEMPLATES_DIR, "memu_logo.png")
        bs_logo = os.path.join(TEMPLATES_DIR, "bluestacks_logo.png")
        ld_logo = os.path.join(TEMPLATES_DIR, "ldplayer_logo.png")
        btn_memu = make_button("MEmu", memu_logo)
        btn_bs = make_button("BlueStacks", bs_logo)
        btn_ld = make_button("LDPlayer", ld_logo)
        btn_ldmi = make_button("LD\nMulti-Instance", ld_logo)
        btn_memu.clicked.connect(lambda: self._choose("memu"))
        btn_bs.clicked.connect(lambda: self._choose("bluestacks"))
        btn_ld.clicked.connect(lambda: self._choose("ldplayer"))
        btn_ldmi.clicked.connect(lambda: self._choose("ldplayer_multi"))
        hbox.addWidget(btn_memu)
        hbox.addWidget(btn_bs)
        hbox.addWidget(btn_ld)
        hbox.addWidget(btn_ldmi)
        vbox = QVBoxLayout(self)
        vbox.addWidget(header)
        vbox.addLayout(hbox)
        vbox.addStretch()
        self.setLayout(vbox)

    def _choose(self, name):
        self.selected = name
        self.accept()

    def getSelection(self):
        return self.selected


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


class TimestampStream(QObject):
    """Qt‑thread‑safe stdout / stderr redirector emitting signal per line."""

    new_line = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._buf = ""

    def write(self, s: str):
        if not s:
            return
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                ts = time.strftime("%H:%M:%S")
                self.new_line.emit(f"{ts} • {line}")

    def flush(self):
        return


LOG_LEVEL_COLORS = {
    "INFO": "#536D80",
    "SUCCESS": "#13775F",
    "WARNING": "#9A6B00",
    "ERROR": "#A82921",
}


def classify_level(line: str) -> str:
    lo = line.lower()
    if any(k in lo for k in ("error", "❌", "failed", "fail", "lỗi", "traceback")):
        return "ERROR"
    if any(k in lo for k in ("warn", "⚠", "cảnh báo", "skipped", "missing")):
        return "WARNING"
    if any(k in lo for k in ("success", "✅", "ready", "confirmed", "hoàn tất",
                             "done", " complete", " ok", "sẵn sàng")):
        return "SUCCESS"
    return "INFO"


def load_settings():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "gold_threshold": 65000,
        "elixir_threshold": 65000,
        "dark_elixir_threshold": 500,
        "upgrade_wall": False,
        "wall_level": 5,
        "wall_gold_threshold": 5000000,
        "wall_elixir_threshold": 5000000,
        "enable_clan_games": False,
        "request_troops": True,
        "attack": "Dragon_Attack",
        "train_mode": "smart",
        "quick_slot": 1,
        "enable_stats": False,
        "enable_clan_capital": False,
        "capital_hall_level": 9,
    }


def save_settings(cfg: dict):
    try:
        with open(CFG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[WARN] could not save settings: {e}")


def load_attack_assets(name: str):
    img_path = os.path.join(ATTACK_DIR, f"{name}.png")
    desc_path = os.path.join(ATTACK_DIR, f"{name}.txt")
    pix = None
    if os.path.isfile(img_path):
        pix = QPixmap(img_path)
        if pix.width() > 520:
            pix = pix.scaledToWidth(520, Qt.SmoothTransformation)
    desc = ""
    if os.path.isfile(desc_path):
        with open(desc_path, "r", encoding="utf-8", errors="ignore") as fh:
            desc = fh.read().strip()
    return pix, desc


class LDInstancePickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select LDPlayer Instance")
        self.setModal(True)
        self.setFixedSize(520, 380)
        self.setStyleSheet("background:#F2F5F3; border:1px solid #DCE5E1;")
        self.index = None
        self.name = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)
        hdr = QLabel("CHOOSE AN LDPLAYER INSTANCE")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet("color:#193431; font-weight:600; font-size:15px;")
        self.layout.addWidget(hdr)
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "Action"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(False)
        for c in range(3):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Fixed)
        self.layout.addWidget(self.table)
        self._equalize_columns()
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._populate_table)
        btn_row.addWidget(self.refresh_btn)
        self.layout.addLayout(btn_row)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self._populate_table()

    def _attach_bounce_icon(self, btn: QPushButton, base_w: int, base_h: int):
        def set_scale(s: float):
            w = int(base_w * s)
            h = int(base_h * s)
            w = min(w, btn.width())
            h = min(h, btn.height())
            btn.setIconSize(QSize(w, h))

        def on_press():
            anim = QVariantAnimation(btn)
            anim.setDuration(90)
            anim.setStartValue(1.0)
            anim.setEndValue(0.92)
            anim.valueChanged.connect(set_scale)
            anim.start()
            btn._press_anim = anim

        def on_release():
            back = QVariantAnimation(btn)
            back.setDuration(110)
            back.setStartValue(0.92)
            back.setEndValue(1.0)
            back.valueChanged.connect(set_scale)
            back.start()
            btn._release_anim = back

        btn.pressed.connect(on_press)
        btn.released.connect(on_release)

    def _populate_table(self):
        self.table.setRowCount(0)
        rows = list_ld_instances()
        if not rows:
            self.table.setRowCount(1)
            it = QTableWidgetItem("No LDPlayer instances found.")
            it.setFlags(it.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
            self.table.setItem(0, 0, it)
            self.table.setSpan(0, 0, 1, 3)
            return
        logo_path = os.path.join(TEMPLATES_DIR, "ldplayer_logo.png")
        icon = QIcon(logo_path) if os.path.exists(logo_path) else QIcon()
        for r in rows:
            self._add_row(r["index"], r["name"], bool(r["started"]), icon)
        self._equalize_columns()

    def _add_row(self, idx: int, name: str, started: bool, icon: QIcon):
        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(icon, name or f"LDPlayer-{idx}")
        name_item.setData(Qt.UserRole, idx)
        name_item.setData(Qt.UserRole + 1, name)
        name_item.setData(Qt.UserRole + 2, started)
        self.table.setItem(row, 0, name_item)
        status_item = QTableWidgetItem("Running" if started else "Available")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QBrush(QColor("#f0b64c" if started else "#60d394")))
        self.table.setItem(row, 1, status_item)
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFixedSize(120, 40)
        start_png = os.path.join(TEMPLATES_DIR, "Start.png")
        btn.setIcon(QIcon(start_png))
        btn.setIconSize(QSize(120, 40))
        btn.setStyleSheet("QPushButton{border:none;background:transparent;}")
        btn.setProperty("ld_index", idx)
        btn.setProperty("ld_name", name or f"LDPlayer-{idx}")
        btn.setProperty("ld_started", started)
        btn.clicked.connect(self._on_start_clicked)
        cell = QWidget()
        hl = QHBoxLayout(cell)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addStretch()
        hl.addWidget(btn)
        hl.addStretch()
        self.table.setCellWidget(row, 2, cell)
        self.table.setColumnWidth(2, 140)
        self.table.setRowHeight(row, 44)
        self._attach_bounce_icon(btn, 120, 40)

    def _adjust_button_icons(self):
        for row in range(self.table.rowCount()):
            w = self.table.columnWidth(2)
            h = self.table.rowHeight(row)
            widget = self.table.cellWidget(row, 2)
            if isinstance(widget, QPushButton):
                widget.setIconSize(QSize(w, h))

    def _warn_busy(self):
        m = QMessageBox(self)
        m.setIcon(QMessageBox.Warning)
        m.setWindowTitle("Instance Busy")
        m.setText(
            "This instance is currently in use. Please close it or select a different available instance."
        )
        m.setStyleSheet("QLabel{ color: white; }")
        m.exec_()

    def _on_start_clicked(self):
        btn = self.sender()
        idx = btn.property("ld_index")
        name = btn.property("ld_name")
        started = bool(btn.property("ld_started"))
        if started:
            self._warn_busy()
            return
        self.index = int(idx)
        self.name = str(name)
        self.accept()

    def _on_row_double_clicked(self, row: int, _col: int):
        item = self.table.item(row, 0)
        if not item:
            return
        started = bool(item.data(Qt.UserRole + 2))
        if started:
            self._warn_busy()
            return
        self.index = int(item.data(Qt.UserRole))
        self.name = str(item.data(Qt.UserRole + 1) or f"LDPlayer-{self.index}")
        self.accept()

    def _equalize_columns(self):
        total = max(0, self.table.viewport().width())
        each = max(120, total // 3)
        for c in range(3):
            self.table.setColumnWidth(c, each)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, self._adjust_button_icons)
        QTimer.singleShot(0, self._equalize_columns)


class TitleBar(QWidget):
    """Frameless-window title bar with drag and double-click maximize."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPos() - self.window().frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        parent = self.window()
        if hasattr(parent, "_toggle_maximized"):
            parent._toggle_maximized()
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
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

    # ---------------------------------------------------------- accounts
    def _account_manager(self):
        return SharedPrefsManager()

    def _account_busy(self) -> bool:
        if self._worker and self._worker.is_alive():
            QMessageBox.warning(
                self, "Bot đang chạy",
                "Hãy Stop bot trước khi Pull/Push/Switch account."
            )
            return True
        return False

    def _build_accounts_tab(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        top = QVBoxLayout()
        top.setSpacing(6)
        prof_row = QHBoxLayout()
        lbl = QLabel("Profile:")
        lbl.setStyleSheet("color:#193431; font-weight:600;")
        prof_row.addWidget(lbl)
        self.acc_profile_combo = QComboBox()
        self.acc_profile_combo.setEditable(True)
        self.acc_profile_combo.setMinimumWidth(180)
        prof_row.addWidget(self.acc_profile_combo, 1)
        top.addLayout(prof_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.addWidget(QLabel("Slot:"))
        self.acc_slot_spin = QSpinBox()
        self.acc_slot_spin.setRange(1, 5)
        self.acc_slot_spin.setFixedWidth(46)
        btn_row.addWidget(self.acc_slot_spin)
        self.acc_pull_btn = QPushButton("Pull")
        self.acc_pull_btn.setToolTip("Pull shared_prefs của account hiện tại")
        self.acc_push_btn = QPushButton("Push")
        self.acc_push_btn.setToolTip("Push profile đang chọn vào game")
        self.acc_switch_btn = QPushButton("Switch")
        self.acc_switch_btn.setToolTip("Chuyển sang profile đang chọn")
        self.acc_refresh_btn = QPushButton("Refresh")
        self.acc_refresh_btn.setToolTip("Tải lại danh sách profile")
        self.acc_delete_btn = QPushButton("Delete")
        self.acc_delete_btn.setToolTip("Xoá profile đang chọn")
        for b in (self.acc_pull_btn, self.acc_push_btn, self.acc_switch_btn,
                  self.acc_refresh_btn, self.acc_delete_btn):
            b.setFixedHeight(26)
            btn_row.addWidget(b)
        btn_row.addStretch()
        top.addLayout(btn_row)
        root.addLayout(top)

        status = QHBoxLayout()
        self.acc_current_lbl = QLabel("Current: (chưa đặt)")
        self.acc_current_lbl.setStyleSheet("color:#13775F; font-weight:600;")
        status.addWidget(self.acc_current_lbl)
        status.addStretch()
        self.acc_root_lbl = QLabel("Root: kiểm tra khi dùng")
        self.acc_root_lbl.setStyleSheet("color:#657877; font-size:9px;")
        status.addWidget(self.acc_root_lbl)
        root.addLayout(status)

        grp = QGroupBox("Switch Accounts")
        g = QGridLayout(grp)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)

        self.switch_enable_chk = QCheckBox("Enable Switch Accounts")
        self.switch_wait_cc_chk = QCheckBox("Switch While Waiting")
        g.addWidget(self.switch_enable_chk, 0, 0, 1, 2)
        self.switch_wait_cc_chk.setToolTip("Chưa hỗ trợ tự động; chỉ lưu cấu hình.")
        g.addWidget(self.switch_wait_cc_chk, 0, 2, 1, 2)

        g.addWidget(QLabel("Accounts:"), 1, 0)
        self.switch_total_spin = QSpinBox()
        self.switch_total_spin.setRange(2, MAX_ACCOUNTS)
        g.addWidget(self.switch_total_spin, 1, 1)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_row.addWidget(QLabel("Mode:"))
        self.switch_shared_radio = QRadioButton("Shared_prefs")
        self.switch_scid_radio = QRadioButton("Supercell ID")
        self.switch_shared_radio.setToolTip(
            "Tự động switch bằng shared_prefs (khuyến nghị).")
        self.switch_scid_radio.setToolTip(
            "Supercell ID: không cần root, dùng màn hình Switch Account trong game.")
        self.switch_mode_group = QButtonGroup(self)
        self.switch_mode_group.addButton(self.switch_shared_radio)
        self.switch_mode_group.addButton(self.switch_scid_radio)
        mode_row.addWidget(self.switch_shared_radio)
        mode_row.addWidget(self.switch_scid_radio)
        mode_row.addStretch()
        g.addLayout(mode_row, 1, 2, 1, 2)

        g.addWidget(QLabel("Attacks / acc:"), 2, 0)
        self.switch_max_spin = QSpinBox()
        self.switch_max_spin.setRange(1, 100)
        self.switch_max_spin.setToolTip(
            "Số trận mặc định cho mỗi account. Account nào có ô 'Trận' riêng "
            "(khác 0) sẽ dùng số đó.")
        g.addWidget(self.switch_max_spin, 2, 1)

        trig_row = QHBoxLayout()
        trig_row.setSpacing(6)
        trig_row.addWidget(QLabel("Trigger:"))
        self.switch_by_attacks_chk = QCheckBox("By attacks")
        self.switch_by_time_chk = QCheckBox("By time")
        self.switch_interval_spin = QSpinBox()
        self.switch_interval_spin.setRange(1, 1440)
        self.switch_interval_spin.setSuffix(" min")
        self.switch_interval_spin.setFixedWidth(80)
        trig_row.addWidget(self.switch_by_attacks_chk)
        trig_row.addWidget(self.switch_by_time_chk)
        trig_row.addWidget(self.switch_interval_spin)
        trig_row.addStretch()
        g.addLayout(trig_row, 3, 0, 1, 4)

        full_row = QHBoxLayout()
        full_row.setSpacing(6)
        self.switch_by_full_chk = QCheckBox("By full 3 storages")
        self.switch_by_full_chk.setToolTip(
            "Chuyển account khi cả 3 kho (vàng, tiêu, DE) đầy. "
            "Dùng template gold/elixir/DE_collector_full.png.")
        full_row.addWidget(self.switch_by_full_chk)
        full_row.addWidget(QLabel("Wait:"))
        self.switch_full_wait_spin = QSpinBox()
        self.switch_full_wait_spin.setRange(1, 1440)
        self.switch_full_wait_spin.setSuffix(" min")
        self.switch_full_wait_spin.setFixedWidth(80)
        self.switch_full_wait_spin.setToolTip(
            "Nếu đầy kho mà không còn account khác: treo online và kiểm tra "
            "lại sau số phút này.")
        full_row.addWidget(self.switch_full_wait_spin)
        full_row.addStretch()
        g.addLayout(full_row, 4, 0, 1, 4)

        body = QVBoxLayout()
        body.setSpacing(6)
        rows_box = QVBoxLayout()
        rows_box.setSpacing(3)
        header = QHBoxLayout()
        h1 = QLabel("Acc")
        h1.setFixedWidth(70)
        h2 = QLabel("Profile")
        h3 = QLabel("Trận")
        h3.setFixedWidth(60)
        h4 = QLabel("Status")
        h4.setFixedWidth(70)
        header.addWidget(h1)
        header.addWidget(h2, 1)
        header.addWidget(h3)
        header.addWidget(h4)
        rows_box.addLayout(header)

        self.switch_rows = []
        for i in range(MAX_ACCOUNTS):
            row = QHBoxLayout()
            cb = QCheckBox(f"Acc {i + 1}.")
            cb.setFixedWidth(70)
            combo = QComboBox()
            combo.setMinimumWidth(120)
            atk = QSpinBox()
            atk.setRange(0, 200)
            atk.setFixedWidth(60)
            atk.setToolTip(
                "Số trận trước khi đổi account. 0 = dùng 'Attacks / acc'.")
            status_lbl = QLabel("")
            status_lbl.setFixedWidth(70)
            row.addWidget(cb)
            row.addWidget(combo, 1)
            row.addWidget(atk)
            row.addWidget(status_lbl)
            for widget in (cb, combo, atk, status_lbl):
                widget.setFixedHeight(24)
            rows_box.addLayout(row)
            self.switch_rows.append({
                "cb": cb, "combo": combo, "atk": atk,
                "status": status_lbl, "row": row,
            })

        self.switch_page_btn = QPushButton(">")
        self.switch_page_btn.setFixedWidth(32)
        rows_box.addWidget(self.switch_page_btn, 0, Qt.AlignLeft)
        rows_box.addStretch(1)
        body.addLayout(rows_box)

        self.switch_log = QTextEdit()
        self.switch_log.setReadOnly(True)
        self.switch_log.setFont(QFont("Consolas", 8))
        self.switch_log.setStyleSheet(
            "background:#FFFFFF; color:#193431; border:1px solid #DCE5E1;"
            " border-radius:5px; padding:4px;")
        self.switch_log.setMinimumHeight(80)
        self.switch_log.setMaximumHeight(120)
        body.addWidget(self.switch_log)
        g.addLayout(body, 5, 0, 1, 4)
        root.addWidget(grp, 1)

        self.acc_mode_note = QLabel(
            "Supercell ID: KHÔNG cần root. Shared_prefs: cần root/adb root."
        )
        self.acc_mode_note.setWordWrap(True)
        self.acc_mode_note.setStyleSheet("color:#657877; font-size:9px;")
        root.addWidget(self.acc_mode_note)

        self.acc_refresh_btn.clicked.connect(self._refresh_accounts)
        self.acc_pull_btn.clicked.connect(self._acc_pull)
        self.acc_push_btn.clicked.connect(self._acc_push)
        self.acc_switch_btn.clicked.connect(self._acc_switch)
        self.acc_delete_btn.clicked.connect(self._acc_delete)
        self.switch_page_btn.clicked.connect(self._switch_page)
        self.switch_total_spin.valueChanged.connect(self._save_switch_ui)
        self.switch_max_spin.valueChanged.connect(self._save_switch_ui)
        self.switch_by_attacks_chk.toggled.connect(self._save_switch_ui)
        self.switch_by_time_chk.toggled.connect(self._save_switch_ui)
        self.switch_by_full_chk.toggled.connect(self._save_switch_ui)
        self.switch_interval_spin.valueChanged.connect(self._save_switch_ui)
        self.switch_full_wait_spin.valueChanged.connect(self._save_switch_ui)
        self.switch_enable_chk.toggled.connect(self._save_switch_ui)
        self.switch_wait_cc_chk.toggled.connect(self._save_switch_ui)
        self.switch_shared_radio.toggled.connect(self._save_switch_ui)
        self.switch_scid_radio.toggled.connect(self._save_switch_ui)
        for row in self.switch_rows:
            row["cb"].toggled.connect(self._save_switch_ui)
            row["atk"].valueChanged.connect(self._save_switch_ui)
            row["combo"].currentTextChanged.connect(self._save_switch_ui)

        return w

    def _account_log(self, text):
        if hasattr(self, "switch_log"):
            import time
            self.switch_log.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def _current_profile_text(self):
        return str(self._switch_cfg.get("current_profile", "")).strip()

    def _set_current_profile(self, name):
        self._switch_cfg["current_profile"] = name or ""
        save_switch_config(self._switch_cfg)
        if hasattr(self, "acc_current_lbl"):
            self.acc_current_lbl.setText(
                f"Current: {name or '(chưa đặt)'}")

    def _refresh_accounts(self, silent=False):
        if not hasattr(self, "acc_profile_combo"):
            return
        try:
            mgr = self._account_manager()
            profiles = mgr.list_profiles()
            names = [p["name"] for p in profiles]
            current_sel = self.acc_profile_combo.currentData()
            self.acc_profile_combo.blockSignals(True)
            self.acc_profile_combo.clear()
            for p in profiles:
                label = p["name"]
                if p.get("files"):
                    label += f"  •  {p['files']} files"
                self.acc_profile_combo.addItem(label, p["name"])
            if current_sel:
                i = self.acc_profile_combo.findData(current_sel)
                if i >= 0:
                    self.acc_profile_combo.setCurrentIndex(i)
            elif self.acc_profile_combo.count():
                self.acc_profile_combo.setCurrentIndex(0)
            self.acc_profile_combo.blockSignals(False)

            for row in self.switch_rows:
                combo = row["combo"]
                old = combo.currentText()
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("")
                combo.addItems(names)
                if old:
                    i = combo.findText(old)
                    if i >= 0:
                        combo.setCurrentIndex(i)
                combo.blockSignals(False)

            if getattr(main, "host", None):
                self.acc_root_lbl.setText(mgr.root_label())
            else:
                self.acc_root_lbl.setText("Root: chưa chọn emulator")
            self.acc_root_lbl.setStyleSheet("color:#657877; font-size:9px;")

            # First-run convenience: assign available profiles to account rows.
            cfg = self._switch_cfg
            if names and not any(a.get("profile") for a in cfg.get("accounts", [])):
                for i in range(min(int(cfg.get("total_accounts", 2)),
                                   len(names), len(cfg.get("accounts", [])))):
                    cfg["accounts"][i]["profile"] = names[i]
                    cfg["accounts"][i]["enabled"] = True
                save_switch_config(cfg)
            # Make sure there is a current profile so auto-switch can rotate.
            if names and not str(cfg.get("current_profile", "")).strip():
                cfg["current_profile"] = names[0]
                save_switch_config(cfg)
                if hasattr(self, "acc_current_lbl"):
                    self.acc_current_lbl.setText(f"Current: {names[0]}")

            self._load_switch_ui()
        except Exception as e:
            self.acc_root_lbl.setText(f"Lỗi: {e}")
            self.acc_root_lbl.setStyleSheet("color:#e05353;")
            if not silent:
                QMessageBox.warning(self, "Account", str(e))
        finally:
            self._loading_switch_ui = False

    def _load_switch_ui(self):
        cfg = self._switch_cfg
        widgets = (self.switch_enable_chk, self.switch_wait_cc_chk,
                   self.switch_total_spin, self.switch_max_spin,
                   self.switch_by_attacks_chk, self.switch_by_time_chk,
                   self.switch_by_full_chk, self.switch_full_wait_spin,
                   self.switch_interval_spin)
        for w in widgets:
            w.blockSignals(True)
        self.switch_enable_chk.setChecked(bool(cfg.get("enabled")))
        self.switch_wait_cc_chk.setChecked(bool(cfg.get("switch_while_waiting")))
        self.switch_total_spin.setValue(int(cfg.get("total_accounts", 2)))
        self.switch_max_spin.setValue(int(cfg.get("consecutive_attacks", 2)))
        self.switch_by_attacks_chk.setChecked(
            bool(cfg.get("use_attack_limit", True)))
        self.switch_by_time_chk.setChecked(
            bool(cfg.get("use_time_schedule", False)))
        self.switch_by_full_chk.setChecked(
            bool(cfg.get("use_storage_full", False)))
        self.switch_full_wait_spin.setValue(
            int(cfg.get("storage_full_wait_minutes", 10)))
        self.switch_interval_spin.setValue(
            int(cfg.get("schedule_minutes", 60)))
        if cfg.get("mode") == "supercell":
            self.switch_scid_radio.setChecked(True)
        else:
            self.switch_shared_radio.setChecked(True)

        accounts = cfg.get("accounts", [])
        for i, row in enumerate(self.switch_rows):
            item = accounts[i] if i < len(accounts) else {"enabled": False, "profile": ""}
            row["cb"].blockSignals(True)
            row["combo"].blockSignals(True)
            row["atk"].blockSignals(True)
            row["cb"].setChecked(bool(item.get("enabled")))
            prof = item.get("profile", "")
            j = row["combo"].findText(prof)
            if j >= 0:
                row["combo"].setCurrentIndex(j)
            else:
                row["combo"].setCurrentText(prof)
            row["atk"].setValue(int(item.get("attacks", 0) or 0))
            row["cb"].blockSignals(False)
            row["combo"].blockSignals(False)
            row["atk"].blockSignals(False)

        for w in widgets:
            w.blockSignals(False)
        if hasattr(self, "acc_current_lbl"):
            self.acc_current_lbl.setText(
                f"Current: {self._current_profile_text() or '(chưa đặt)'}")
        self._update_switch_rows()
        self._apply_mode_ui()

    def _apply_mode_ui(self):
        if not hasattr(self, "switch_shared_radio"):
            return
        is_shared = self.switch_shared_radio.isChecked()
        self.acc_profile_combo.setEnabled(is_shared)
        self.acc_pull_btn.setEnabled(is_shared)
        self.acc_push_btn.setEnabled(is_shared)
        self.acc_slot_spin.setEnabled(not is_shared)
        for row in self.switch_rows:
            row["combo"].setEnabled(is_shared)
        if is_shared:
            self.acc_mode_note.setText(
                "Shared_prefs: dùng adbd root sẵn có (MEmu/LDPlayer), "
                "không cần root thủ công. Nếu emulator không có adbd root, "
                "hãy dùng Supercell ID.")
        else:
            self.acc_mode_note.setText(
                "Supercell ID: KHÔNG cần root. Chọn Slot 1-5 rồi bấm Switch now. "
                "Slot tương ứng thứ tự account trong màn hình Switch Account của game.")

    def _save_switch_ui(self, *args):
        if getattr(self, "_loading_switch_ui", False):
            return
        cfg = self._switch_cfg
        cfg["enabled"] = self.switch_enable_chk.isChecked()
        cfg["switch_while_waiting"] = self.switch_wait_cc_chk.isChecked()
        cfg["total_accounts"] = int(self.switch_total_spin.value())
        cfg["consecutive_attacks"] = int(self.switch_max_spin.value())
        was_time = bool(cfg.get("use_time_schedule", False))
        cfg["use_attack_limit"] = self.switch_by_attacks_chk.isChecked()
        cfg["use_time_schedule"] = self.switch_by_time_chk.isChecked()
        cfg["use_storage_full"] = self.switch_by_full_chk.isChecked()
        cfg["storage_full_wait_minutes"] = int(
            self.switch_full_wait_spin.value())
        cfg["schedule_minutes"] = int(self.switch_interval_spin.value())
        if cfg["use_time_schedule"] and not was_time:
            cfg["last_switch_ts"] = time.time()
        cfg["mode"] = "supercell" if self.switch_scid_radio.isChecked() else "shared_prefs"
        for i, row in enumerate(self.switch_rows):
            cfg["accounts"][i] = {
                "enabled": row["cb"].isChecked(),
                "profile": row["combo"].currentText().strip(),
                "attacks": int(row["atk"].value()),
            }
        save_switch_config(cfg)
        self._update_switch_rows()
        self._apply_mode_ui()

    def _update_switch_rows(self):
        if not hasattr(self, "switch_total_spin"):
            return
        total = int(self.switch_total_spin.value())
        for i, row in enumerate(self.switch_rows):
            visible = (
                self._switch_page_idx * ACCOUNTS_PER_PAGE
                <= i
                < min(total, (self._switch_page_idx + 1) * ACCOUNTS_PER_PAGE)
            )
            for widget in (row["cb"], row["combo"], row["atk"], row["status"]):
                widget.setVisible(visible)
        pages = max(1, (total + ACCOUNTS_PER_PAGE - 1) // ACCOUNTS_PER_PAGE)
        self.switch_page_btn.setVisible(pages > 1)
        self.switch_page_btn.setText(">" if self._switch_page_idx == 0 else "<")

    def _switch_page(self):
        total = int(self.switch_total_spin.value())
        pages = max(1, (total + ACCOUNTS_PER_PAGE - 1) // ACCOUNTS_PER_PAGE)
        self._switch_page_idx = (self._switch_page_idx + 1) % pages
        self._update_switch_rows()

    def _selected_profile(self):
        data = self.acc_profile_combo.currentData()
        if data:
            return str(data)
        return self.acc_profile_combo.currentText().strip()

    def _acc_pull(self):
        if self._account_busy():
            return
        if self.switch_scid_radio.isChecked():
            QMessageBox.information(
                self, "Supercell ID",
                "Chế độ Supercell ID không dùng Pull/Push.\n"
                "Dùng Switch now (Slot 1-5)."
            )
            return
        name = self._selected_profile()
        if not name:
            QMessageBox.warning(self, "Profile", "Chọn hoặc nhập tên profile trước.")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._account_manager().pull_profile(name)
            self._set_current_profile(name)
            self._account_log(f"Pull OK: {name}")
            self._refresh_accounts(silent=True)
        except Exception as e:
            QMessageBox.critical(self, "Pull shared_prefs", str(e))
            self._account_log(f"Pull FAIL: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _acc_push(self):
        if self._account_busy():
            return
        if self.switch_scid_radio.isChecked():
            QMessageBox.information(
                self, "Supercell ID",
                "Chế độ Supercell ID không dùng Pull/Push.\n"
                "Dùng Switch now (Slot 1-5)."
            )
            return
        name = self._selected_profile()
        if not name:
            QMessageBox.warning(self, "Profile", "Chọn profile trước.")
            return
        ans = QMessageBox.question(
            self, "Push shared_prefs",
            f"Đưa profile '{name}' vào game?\nGame sẽ restart.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._account_manager().push_profile(
                name, current_profile=self._current_profile_text())
            self._set_current_profile(name)
            self._account_log(f"Push OK: {name}")
            self._refresh_accounts(silent=True)
        except Exception as e:
            QMessageBox.critical(self, "Push shared_prefs", str(e))
            self._account_log(f"Push FAIL: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _acc_switch(self):
        if self._account_busy():
            return

        if self.switch_scid_radio.isChecked():
            slot = int(self.acc_slot_spin.value())
            ans = QMessageBox.question(
                self, "Switch Supercell ID",
                f"Chuyển sang account slot {slot}?\n"
                "Dùng màn hình Switch Account trong game (không cần root).",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                from COCbot.game.account.ready_villages import switch_to_village
                switch_to_village(slot)
                self._switch_cfg["current_slot"] = slot
                save_switch_config(self._switch_cfg)
                self._account_log(f"Switch SCID OK: slot {slot}")
            except Exception as e:
                QMessageBox.critical(self, "Switch Supercell ID", str(e))
                self._account_log(f"Switch SCID FAIL: {e}")
            finally:
                QApplication.restoreOverrideCursor()
            return

        target = self._selected_profile()
        if not target:
            QMessageBox.warning(self, "Profile", "Chọn profile đích trước.")
            return
        current = self._current_profile_text()
        if not current:
            QMessageBox.warning(
                self, "Switch account",
                "Chưa đặt Current profile.\nHãy Pull current trước để lưu "
                "account đang mở, tránh mất tiến độ."
            )
            return
        ans = QMessageBox.question(
            self, "Switch account",
            f"Switch {current} -> '{target}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self._account_manager().switch_profile(current, target)
            self._set_current_profile(target)
            self._account_log(f"Switch OK: {current} -> {target}")
            self._refresh_accounts(silent=True)
        except Exception as e:
            QMessageBox.critical(self, "Switch account", str(e))
            self._account_log(f"Switch FAIL: {e}")
        finally:
            QApplication.restoreOverrideCursor()
    def _acc_delete(self):
        name = self._selected_profile()
        if not name:
            QMessageBox.warning(self, "Profile", "Chọn profile trước.")
            return
        ans = QMessageBox.question(
            self, "Delete profile", f"Xoá profile '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        try:
            self._account_manager().delete_profile(name)
            if self._current_profile_text() == name:
                self._set_current_profile("")
            self._refresh_accounts(silent=True)
        except Exception as e:
            QMessageBox.critical(self, "Delete profile", str(e))

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
        self.attack_images = {
            k: load_attack_assets(k) for k in ["Dragon_Attack", "ElectroDragon_Attack"]
        }
        hdrF = QFont("Segoe UI", 12, QFont.Bold)
        labF = QFont("Segoe UI", 10, QFont.Bold)

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
        header_layout.addSpacing(2)

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

        # ===== TAB 0: Logs tab =====
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.setContentsMargins(0, 10, 0, 0)
        logs_layout.setSpacing(12)

        # Bot log card
        bot_card = QFrame()
        bot_card.setObjectName("card")
        bot_card_v = QVBoxLayout(bot_card)
        bot_card_v.setContentsMargins(12, 10, 12, 8)
        bot_card_v.setSpacing(6)
        bot_head = QHBoxLayout()
        bot_head.setSpacing(8)
        bot_title = QLabel("Bot log")
        bot_title.setStyleSheet("font-size:14px; font-weight:600; color:#193431;")
        bot_head.addWidget(bot_title)
        bot_head.addStretch()
        self.log_filter = QComboBox()
        self.log_filter.addItems(["All events", "INFO", "SUCCESS", "WARNING", "ERROR"])
        self.log_filter.setFixedWidth(96)
        self.log_filter.currentTextChanged.connect(self._on_log_filter_changed)
        bot_head.addWidget(self.log_filter)
        export_btn = QPushButton("Export")
        export_btn.setFixedHeight(28)
        export_btn.clicked.connect(self._export_log)
        bot_head.addWidget(export_btn)
        bot_card_v.addLayout(bot_head)

        self.log = QTextEdit()
        self.log.setObjectName("logView")
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setMinimumHeight(240)
        bot_card_v.addWidget(self.log, 1)

        bot_foot = QHBoxLayout()
        bot_foot.setSpacing(6)
        self.auto_scroll_chk = QCheckBox("Auto-scroll")
        self.auto_scroll_chk.setChecked(True)
        bot_foot.addWidget(self.auto_scroll_chk)
        bot_foot.addStretch()
        self.log_count_lbl = QLabel("0 events · All systems ready")
        self.log_count_lbl.setStyleSheet("color:#657877; font-size:10px;")
        bot_foot.addWidget(self.log_count_lbl)
        bot_card_v.addLayout(bot_foot)
        logs_layout.addWidget(bot_card, 65)

        # Attack log card
        atk_card = QFrame()
        atk_card.setObjectName("card")
        atk_v = QVBoxLayout(atk_card)
        atk_v.setContentsMargins(12, 10, 12, 10)
        atk_v.setSpacing(6)
        atk_head = QHBoxLayout()
        atk_head.setSpacing(8)
        atk_title = QLabel("Attack log")
        atk_title.setStyleSheet("font-size:14px; font-weight:600; color:#193431;")
        atk_head.addWidget(atk_title)
        self.attack_count_lbl = QLabel("0")
        self.attack_count_lbl.setStyleSheet(
            "background:#EEF2F6; color:#536D80; border-radius:3px;"
            " padding:1px 5px; font-size:8px; font-weight:600;")
        atk_head.addWidget(self.attack_count_lbl)
        atk_head.addStretch()
        atk_sub = QLabel("This session")
        atk_sub.setStyleSheet("color:#657877; font-size:10px;")
        atk_head.addWidget(atk_sub)
        atk_v.addLayout(atk_head)

        self.attack_table = QTableWidget(0, 7)
        self.attack_table.setHorizontalHeaderLabels(
            ["TIME", "MODE", "GOLD", "ELIXIR", "DARK", "TROPHIES", "BONUS"])
        self.attack_table.verticalHeader().setVisible(False)
        self.attack_table.setShowGrid(False)
        self.attack_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.attack_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.attack_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.attack_table.verticalHeader().setDefaultSectionSize(22)
        self.attack_table.setMinimumHeight(100)
        atk_v.addWidget(self.attack_table, 1)
        self._reset_attack_table()
        logs_layout.addWidget(atk_card, 35)

        # ===== TAB 1: General tab =====
        gen_tab = QWidget()
        grid = QGridLayout(gen_tab)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        def line():
            l = QFrame()
            l.setFrameShape(QFrame.HLine)
            l.setStyleSheet("color:#666;")
            return l

        row = 0
        self.gold_entry = QLineEdit(str(self.settings.get("gold_threshold", 65000)))
        self.elixir_entry = QLineEdit(
            str(self.settings.get("elixir_threshold", 65000))
        )
        self.dark_entry = QLineEdit(
            str(self.settings.get("dark_elixir_threshold", 5))
        )
        for e in [self.gold_entry, self.elixir_entry, self.dark_entry]:
            e.setFont(labF)
            e.setFixedWidth(120)

        icon_gold_lbl = QLabel()
        pix = QPixmap(os.path.join(TEMPLATES_DIR, "icon_gold.png")).scaledToWidth(
            24, Qt.SmoothTransformation
        )
        icon_gold_lbl.setPixmap(pix)
        gold_container = QWidget()
        gold_hlay = QHBoxLayout(gold_container)
        gold_hlay.setContentsMargins(0, 0, 0, 0)
        gold_hlay.setSpacing(6)
        gold_hlay.addWidget(icon_gold_lbl)
        lbl_gold = QLabel("Gold:")
        lbl_gold.setFont(labF)
        lbl_gold.setStyleSheet("color:#193431;")
        gold_hlay.addWidget(lbl_gold)
        gold_hlay.addStretch()
        grid.addWidget(gold_container, row, 0)
        grid.addWidget(self.gold_entry, row, 1)
        row += 1

        icon_elixir_lbl = QLabel()
        pix2 = QPixmap(os.path.join(TEMPLATES_DIR, "icon_elixir.png")).scaledToWidth(
            24, Qt.SmoothTransformation
        )
        icon_elixir_lbl.setPixmap(pix2)
        elixir_container = QWidget()
        elixir_hlay = QHBoxLayout(elixir_container)
        elixir_hlay.setContentsMargins(0, 0, 0, 0)
        elixir_hlay.setSpacing(6)
        elixir_hlay.addWidget(icon_elixir_lbl)
        lbl_elixir = QLabel("Elixir:")
        lbl_elixir.setFont(labF)
        lbl_elixir.setStyleSheet("color:#193431;")
        elixir_hlay.addWidget(lbl_elixir)
        elixir_hlay.addStretch()
        grid.addWidget(elixir_container, row, 0)
        grid.addWidget(self.elixir_entry, row, 1)
        row += 1

        icon_de_lbl = QLabel()
        pix3 = QPixmap(os.path.join(TEMPLATES_DIR, "icon_de.png")).scaledToWidth(
            24, Qt.SmoothTransformation
        )
        icon_de_lbl.setPixmap(pix3)
        de_container = QWidget()
        de_hlay = QHBoxLayout(de_container)
        de_hlay.setContentsMargins(0, 0, 0, 0)
        de_hlay.setSpacing(6)
        de_hlay.addWidget(icon_de_lbl)
        lbl_de = QLabel("Dark Elixir:")
        lbl_de.setFont(labF)
        lbl_de.setStyleSheet("color:#193431;")
        de_hlay.addWidget(lbl_de)
        de_hlay.addStretch()
        grid.addWidget(de_container, row, 0)
        grid.addWidget(self.dark_entry, row, 1)
        row += 1

        grid.addWidget(line(), row, 0, 1, 2)
        row += 1

        up_container = QWidget()
        up_layout = QHBoxLayout(up_container)
        up_layout.setContentsMargins(0, 0, 0, 0)
        up_layout.setSpacing(6)
        self.upgrade_chk = QCheckBox("Enable Upgrade Wall")
        self.upgrade_chk.setFont(hdrF)
        self.upgrade_chk.setStyleSheet("color:#193431;")
        self.upgrade_chk.setChecked(self.settings.get("upgrade_wall", False))
        up_layout.addWidget(self.upgrade_chk)
        icon_up_lbl = QLabel()
        pix_up = QPixmap(os.path.join(TEMPLATES_DIR, "icon_up.png")).scaledToWidth(
            16, Qt.SmoothTransformation
        )
        icon_up_lbl.setPixmap(pix_up)
        up_layout.addWidget(icon_up_lbl)
        up_layout.addStretch()
        grid.addWidget(up_container, row, 0, 1, 2)
        row += 1

        self.wall_gold_entry = QLineEdit(
            str(self.settings.get("wall_gold_threshold", 5000000))
        )
        self.wall_elixir_entry = QLineEdit(
            str(self.settings.get("wall_elixir_threshold", 5000000))
        )
        self.wall_level_spin = QSpinBox()
        self.wall_level_spin.setRange(8, 18)
        self.wall_level_spin.setValue(self.settings.get("wall_level", 8))
        for w in [self.wall_gold_entry, self.wall_elixir_entry, self.wall_level_spin]:
            w.setFont(labF)
            w.setFixedWidth(120)

        icon_wall_gold = QLabel()
        pix_wg = QPixmap(os.path.join(TEMPLATES_DIR, "icon_gold.png")).scaledToWidth(
            24, Qt.SmoothTransformation
        )
        icon_wall_gold.setPixmap(pix_wg)
        wg_gold_container = QWidget()
        wg_gold_hlay = QHBoxLayout(wg_gold_container)
        wg_gold_hlay.setContentsMargins(0, 0, 0, 0)
        wg_gold_hlay.setSpacing(6)
        wg_gold_hlay.addWidget(icon_wall_gold)
        lbl_wg_gold = QLabel("Gold Threshold:")
        lbl_wg_gold.setFont(labF)
        lbl_wg_gold.setStyleSheet("color:#193431;")
        wg_gold_hlay.addWidget(lbl_wg_gold)
        wg_gold_hlay.addStretch()
        grid.addWidget(wg_gold_container, row, 0)
        grid.addWidget(self.wall_gold_entry, row, 1)
        row += 1

        icon_wall_elixir = QLabel()
        pix_we = QPixmap(os.path.join(TEMPLATES_DIR, "icon_elixir.png")).scaledToWidth(
            24, Qt.SmoothTransformation
        )
        icon_wall_elixir.setPixmap(pix_we)
        wg_elixir_container = QWidget()
        wg_elixir_hlay = QHBoxLayout(wg_elixir_container)
        wg_elixir_hlay.setContentsMargins(0, 0, 0, 0)
        wg_elixir_hlay.setSpacing(6)
        wg_elixir_hlay.addWidget(icon_wall_elixir)
        lbl_wg_elixir = QLabel("Elixir Threshold:")
        lbl_wg_elixir.setFont(labF)
        lbl_wg_elixir.setStyleSheet("color:#193431;")
        wg_elixir_hlay.addWidget(lbl_wg_elixir)
        wg_elixir_hlay.addStretch()
        grid.addWidget(wg_elixir_container, row, 0)
        grid.addWidget(self.wall_elixir_entry, row, 1)
        row += 1

        icon_wall_level = QLabel()
        pix_wl = QPixmap(os.path.join(TEMPLATES_DIR, "icon_wall.png")).scaledToWidth(
            24, Qt.SmoothTransformation
        )
        icon_wall_level.setPixmap(pix_wl)
        wl_container = QWidget()
        wl_hlay = QHBoxLayout(wl_container)
        wl_hlay.setContentsMargins(0, 0, 0, 0)
        wl_hlay.setSpacing(6)
        wl_hlay.addWidget(icon_wall_level)
        lbl_wl = QLabel("Target Wall Level:")
        lbl_wl.setFont(labF)
        lbl_wl.setStyleSheet("color:#193431;")
        wl_hlay.addWidget(lbl_wl)
        wl_hlay.addStretch()
        grid.addWidget(wl_container, row, 0)
        grid.addWidget(self.wall_level_spin, row, 1)
        row += 1

        grid.addWidget(line(), row, 0, 1, 2)
        row += 1

        req_container = QWidget()
        req_layout = QHBoxLayout(req_container)
        req_layout.setContentsMargins(0, 0, 0, 0)
        req_layout.setSpacing(6)
        self.req_chk = QCheckBox("Enable Request Troops")
        self.req_chk.setFont(hdrF)
        self.req_chk.setStyleSheet("color:#193431;")
        self.req_chk.setChecked(self.settings.get("request_troops", False))
        req_layout.addWidget(self.req_chk)
        icon_cc = QLabel()
        pix_cc = QPixmap(
            os.path.join(TEMPLATES_DIR, "icon_clan_castle.png")
        ).scaledToWidth(28, Qt.SmoothTransformation)
        icon_cc.setPixmap(pix_cc)
        req_layout.addWidget(icon_cc)
        req_layout.addStretch()
        grid.addWidget(req_container, row, 0, 1, 2)
        row += 1

        grid.addWidget(line(), row, 0, 1, 2)
        row += 1

        def set_opacity(wlist, on):
            for w in wlist:
                w.setWindowOpacity(1.0 if on else 0.35)

        wall_widgets = [
            self.wall_gold_entry,
            self.wall_elixir_entry,
            self.wall_level_spin,
        ]
        req_widgets = []

        def apply_state(enabled: bool, widgets):
            for w in widgets:
                w.setEnabled(enabled)
                w.setWindowOpacity(1.0 if enabled else 0.35)

        apply_state(self.upgrade_chk.isChecked(), wall_widgets)
        apply_state(self.req_chk.isChecked(), req_widgets)
        self.upgrade_chk.toggled.connect(lambda on: apply_state(on, wall_widgets))
        self.req_chk.toggled.connect(lambda on: apply_state(on, req_widgets))
        set_opacity(wall_widgets, self.upgrade_chk.isChecked())
        set_opacity(req_widgets, self.req_chk.isChecked())
        self.upgrade_chk.toggled.connect(lambda on: set_opacity(wall_widgets, on))
        self.req_chk.toggled.connect(lambda on: set_opacity(req_widgets, on))

        # ===== TAB 2: Army tab =====
        self.army_tab = ArmyRecipeTab()
        self.army_tab.check_troops_chk.setChecked(
            bool(self.settings.get("check_troops", False))
        )
        self.army_tab.recipe_changed.connect(self._on_army_recipe_changed)

        # ===== TAB 3.5: Accounts / Switch Accounts =====
        self.accounts_tab = self._build_accounts_tab()

        # ===== TAB 4: Clan Games tab =====
        clan_tab = QWidget()
        cg_layout = QVBoxLayout(clan_tab)
        cg_layout.setContentsMargins(12, 12, 12, 12)
        cg_layout.setSpacing(10)
        enable_container = QWidget()
        enable_layout = QHBoxLayout(enable_container)
        enable_layout.setContentsMargins(0, 0, 0, 0)
        enable_layout.setSpacing(6)
        self.clan_games_toggle = QCheckBox("Enable Clan Games")
        self.clan_games_toggle.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.clan_games_toggle.setStyleSheet("color: #193431;")
        self.clan_games_toggle.setChecked(self.settings.get("enable_clan_games", False))
        enable_layout.addWidget(self.clan_games_toggle)
        games_icon_lbl = QLabel()
        pix_games = QPixmap(
            os.path.join(TEMPLATES_DIR, "icon_games.png")
        ).scaledToWidth(50, Qt.SmoothTransformation)
        games_icon_lbl.setPixmap(pix_games)
        enable_layout.addWidget(games_icon_lbl)
        enable_layout.addStretch()
        cg_layout.addWidget(enable_container)
        self.cg_grid_container = QWidget()
        cg_grid_layout = QGridLayout(self.cg_grid_container)
        cg_grid_layout.setContentsMargins(0, 0, 0, 0)
        cg_grid_layout.setHorizontalSpacing(8)
        cg_grid_layout.setVerticalSpacing(8)
        cg_layout.addWidget(self.cg_grid_container)
        cg_layout.addSpacing(6)
        self.cg_full_img_lbl = QLabel()
        pix_cg = QPixmap(os.path.join(TEMPLATES_DIR, "Clan Games.png"))
        pix_cg = pix_cg.scaledToWidth(240, Qt.SmoothTransformation)
        self.cg_full_img_lbl.setPixmap(pix_cg)
        self.cg_full_img_lbl.setAlignment(Qt.AlignCenter)
        cg_layout.addWidget(self.cg_full_img_lbl)

        def _on_clan_toggle(on: bool):
            opacity = 1.0 if on else 0.6
            eff = QGraphicsOpacityEffect()
            eff.setOpacity(opacity)
            self.cg_full_img_lbl.setGraphicsEffect(eff)

        self.clan_games_toggle.toggled.connect(_on_clan_toggle)
        _on_clan_toggle(False)
        cg_layout.addStretch()

        # ===== TAB 5: Clan Capital tab =====
        cc_tab = QWidget()
        cc_layout = QVBoxLayout(cc_tab)
        cc_layout.setContentsMargins(12, 12, 12, 12)
        cc_layout.setSpacing(10)
        cc_en_row = QWidget()
        cc_en_h = QHBoxLayout(cc_en_row)
        cc_en_h.setContentsMargins(0, 0, 0, 0)
        cc_en_h.setSpacing(4)
        self.clan_capital_toggle = QCheckBox("Enable Clan Capital")
        self.clan_capital_toggle.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.clan_capital_toggle.setStyleSheet("color:#193431;")
        self.clan_capital_toggle.setChecked(
            self.settings.get("enable_clan_capital", False)
        )
        cc_en_h.addWidget(self.clan_capital_toggle, 0, Qt.AlignLeft | Qt.AlignVCenter)
        logo_path = os.path.join(TEMPLATES_DIR, "clan_capital_logo.png")
        logo_lbl = QLabel()
        if os.path.exists(logo_path):
            pix_cc_logo = QPixmap(logo_path)
            if not pix_cc_logo.isNull():
                logo_lbl.setPixmap(
                    pix_cc_logo.scaled(
                        44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
        logo_lbl.setContentsMargins(6, 0, 0, 0)
        cc_en_h.addWidget(logo_lbl, 0, Qt.AlignLeft | Qt.AlignVCenter)
        cc_en_h.addStretch(1)
        cc_layout.addWidget(cc_en_row)

        note_lbl = QLabel(
            "Note: If you enable Clan Capital, please use the default scenery "
            "so the bot can detect the Clan Capital boat more reliably."
        )
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet(
            "\n            color: #193431;\n            font-size: 13px;\n"
            "            font-weight: 600;\n            margin-top: 4px;\n        "
        )
        cc_layout.addWidget(note_lbl)

        cc_lvl_row = QWidget()
        cc_lvl_h = QHBoxLayout(cc_lvl_row)
        cc_lvl_h.setContentsMargins(0, 0, 0, 0)
        cc_lvl_h.setSpacing(8)
        lvl_label = QLabel("Capital Hall level:")
        lvl_label.setStyleSheet("color:#193431; font-size:15px; font-weight:600;")
        cc_lvl_h.addWidget(lvl_label, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.cc_level = QSpinBox()
        self.cc_level.setRange(1, 10)
        self.cc_level.setSingleStep(1)
        self.cc_level.setValue(int(self.settings.get("capital_hall_level", 9)))
        self.cc_level.setToolTip("Select your Clan Capital Hall level (1–10).")
        self.cc_level.setFixedSize(90, 34)
        self.cc_level.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        cc_lvl_h.addWidget(self.cc_level, 0, Qt.AlignLeft | Qt.AlignVCenter)
        cc_lvl_h.addStretch(1)
        cc_layout.addWidget(cc_lvl_row)
        cc_layout.addStretch()
        self.cc_level.setEnabled(self.clan_capital_toggle.isChecked())
        self.clan_capital_toggle.toggled.connect(self.cc_level.setEnabled)

        def _cc_toggle_update(on: bool):
            note_lbl.setEnabled(on)
            lvl_label.setEnabled(on)
            self.cc_level.setEnabled(on)

        _cc_toggle_update(self.clan_capital_toggle.isChecked())
        self.clan_capital_toggle.toggled.connect(_cc_toggle_update)

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
        village_tabs.addTab(_scroll(self.accounts_tab), "Accounts")
        village_tabs.currentChanged.connect(
            lambda i: self._refresh_accounts(silent=True) if i == 1 else None)

        settings_tabs = QTabWidget()
        settings_tabs.setObjectName("subTabs")
        settings_tabs.setDocumentMode(True)
        settings_tabs.addTab(_scroll(clan_tab), "Clan Games")
        settings_tabs.addTab(_scroll(cc_tab), "Clan Capital")
        settings_tabs.addTab(_scroll(self.debug_tab), "Debug")

        about_tab = self._build_about_tab()

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

    def _build_about_tab(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 10, 0, 0)
        outer.setSpacing(12)

        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(16, 16, 16, 16)
        cv.setSpacing(8)

        title = QLabel("MyBot PHMOD v15.9")
        title.setStyleSheet("font-size:16px; font-weight:600; color:#193431;")
        cv.addWidget(title)

        subtitle = QLabel("Clash of Clans automation control panel")
        subtitle.setStyleSheet("font-size:11px; color:#657877;")
        cv.addWidget(subtitle)

        desc = QLabel(
            "Bot tự động farm tài nguyên, huấn luyện quân, xin quân, "
            "Clan Games / Clan Capital và chuyển account. "
            "Redline dùng OpenCV fallback, có thể nâng cấp bằng YOLO-seg."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:11px; color:#193431; line-height: 150%;")
        cv.addWidget(desc)

        meta = QLabel(
            "Python 3.13 · PyQt5 · OpenCV · Ultralytics (optional)\n"
            "Freeware · Open source · Không liên kết với Supercell."
        )
        meta.setWordWrap(True)
        meta.setStyleSheet("font-size:10px; color:#657877;")
        cv.addWidget(meta)

        btn_row = QHBoxLayout()
        github_btn = QPushButton("GitHub repository")
        github_btn.clicked.connect(
            lambda: webbrowser.open(
                "https://github.com/lvmai1801it-dev/MyBot_Python"))
        btn_row.addWidget(github_btn)
        btn_row.addStretch()
        cv.addLayout(btn_row)

        outer.addWidget(card)
        outer.addStretch()
        return page

    def _on_army_recipe_changed(self):
        name = self.army_tab.get_active_name()
        print(f"[ARMY] Recipe changed: {name}")

    def _toggle_wall_inputs(self, enabled: bool):
        policy = Qt.StrongFocus if enabled else Qt.NoFocus
        for w in [self.wall_gold_entry, self.wall_elixir_entry, self.wall_level_spin]:
            w.setEnabled(enabled)
            w.setFocusPolicy(policy)

    def _log_line_html(self, level: str, text: str) -> str:
        colour = LOG_LEVEL_COLORS.get(level, LOG_LEVEL_COLORS["INFO"])
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f'<span style="color:{colour};">{safe}</span><br>'

    def _append_log(self, line: str):
        if not line:
            return
        text = str(line).rstrip("\r\n")
        if not text.strip():
            return
        level = classify_level(text)
        self._log_lines.append((level, text))
        if len(self._log_lines) > 4000:
            self._log_lines = self._log_lines[-3000:]
        self._add_attack_row(text)

        if self._log_filter == "All events" or self._log_filter == level:
            self.log.moveCursor(QTextCursor.End)
            self.log.insertHtml(self._log_line_html(level, text))
            if self.auto_scroll_chk.isChecked():
                self.log.moveCursor(QTextCursor.End)

        if hasattr(self, "log_count_lbl"):
            self.log_count_lbl.setText(
                f"{len(self._log_lines)} events · All systems ready")

    def _on_log_filter_changed(self, value: str):
        self._log_filter = value or "All events"
        self.log.clear()
        for level, text in self._log_lines:
            if self._log_filter == "All events" or self._log_filter == level:
                self.log.insertHtml(self._log_line_html(level, text))
        self.log.moveCursor(QTextCursor.End)

    def _export_log(self):
        default = os.path.join(
            os.path.expanduser("~"), "mybot-log.txt")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export bot log", default, "Text files (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                for level, text in self._log_lines:
                    fh.write(f"[{level}] {text}\n")
            print(f"[UI] Log exported: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Export", f"Không ghi được log:\n{e}")

    def _reset_attack_table(self):
        self.attack_table.clearSpans()
        self.attack_table.setRowCount(0)
        self.attack_table.insertRow(0)
        item = QTableWidgetItem(
            "No attacks yet — Start the bot to see results here.")
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QBrush(QColor("#657877")))
        self.attack_table.setItem(0, 0, item)
        self.attack_table.setSpan(0, 0, 1, 7)
        self._attack_placeholder = True
        if hasattr(self, "attack_count_lbl"):
            self.attack_count_lbl.setText("0")

    def _add_attack_row(self, text: str):
        match = re.search(
            r"\[LOOT\]\s*GOLD:\s*([\d,]+)\s*ELIXIR:\s*([\d,]+)"
            r"\s*DARK_ELIXIR:\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )
        if not match or not hasattr(self, "attack_table"):
            return
        if getattr(self, "_attack_placeholder", False):
            self.attack_table.clearSpans()
            self.attack_table.removeRow(0)
            self._attack_placeholder = False
        time_str = text.split("•")[0].strip() if "•" in text else time.strftime("%H:%M:%S")
        attack = str(self.settings.get("attack", "") or "")
        mode = {
            "Dragon_Attack": "Dragon",
            "ElectroDragon_Attack": "E-Dragon",
        }.get(attack, attack or "Attack")
        values = [
            time_str,
            mode,
            self._fmt_number(match.group(1)),
            self._fmt_number(match.group(2)),
            self._fmt_number(match.group(3)),
            "—",
            "—",
        ]
        row = self.attack_table.rowCount()
        self.attack_table.insertRow(row)
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(
                Qt.AlignVCenter | (Qt.AlignLeft if col < 2 else Qt.AlignRight))
            self.attack_table.setItem(row, col, item)
        self.attack_count_lbl.setText(str(row + 1))
        self.attack_table.scrollToBottom()

    @staticmethod
    def _fmt_number(value: str) -> str:
        try:
            return f"{int(str(value).replace(',', '')):,}"
        except Exception:
            return str(value)

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
    app = QApplication.instance()
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
