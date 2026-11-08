# src/gui/bot_gui.py
try:
    import torch
except Exception:
    pass

import ctypes
import os
import sys

import core.paths

from gui.army_recipe_tab import ArmyRecipeTab
from gui.debug_tab import DebugTab

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

import glob
import json
import logging
import tempfile
import threading
import time
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
import atexit
import socket
import traceback
import webbrowser
from pathlib import Path

from PyQt5.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRect,
    QSize,
    QTimer,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPixmap, QTextCursor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from utils.updater import Updater

import main
from COCbot.emulator.ldplayer_manager import list_ld_instances
from COCbot.routines.ready_villages import prepare_accounts, save_village_config
from gui.qt_thread_compat import QtThreadCompat
from gui.stats_tab import StatsTab
from gui.village_wiz import run_village_wizard
from gui.wizard_bridge import bridge
from COCbot.core.controls import pause_bot, resume_bot
from COCbot.utils.stats_manager import  zero_all_stats_files

BASE_DIR = str(core.paths.SRC_DIR)
APP_DIR = BASE_DIR
ATTACK_DIR = str(core.paths.ATTACKS_DIR)
BG = str(core.paths.TEMPLATE_DIR)
TEMPLATES_DIR = BG
CFG_PATH = str(core.paths.SETTINGS_JSON)
profiles_dir = str(core.paths.PROFILES_DIR)
json_paths = glob.glob(os.path.join(profiles_dir, "Village_*.json"))

MEMU = "127.0.0.1:21503"
BLUESTACKS = "127.0.0.1:5556"
LDPLAYER = "127.0.0.1:5555"


class EmulatorSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = None
        self.setWindowTitle("Select Emulator")
        self.setModal(True)
        self.setFixedSize(820, 260)
        self.setStyleSheet(
            "\n            QDialog {\n                background-color: #2b2b2b;\n"
            "                border-radius: 12px;\n                background-image: qradialgradient(\n"
            "                    cx:0.5, cy:0.5, radius:1.0,\n"
            "                    fx:0.5, fy:0.5,\n"
            "                    stop:0 rgba(60,60,60,255),\n"
            "                    stop:1 rgba(43,43,43,200)\n"
            "                );\n            }\n        "
        )
        header = QLabel("Choose your emulator", self)
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header.setStyleSheet("color:#FFFFFF;")
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
                "\n                QToolButton { color:#EFEFEF; background:transparent; border:none; }\n"
                "                QToolButton:hover { color:#FFD660; }\n            "
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


class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_geom = None
        self._hovered = False
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(120)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def showEvent(self, ev):
        super().showEvent(ev)
        if self._base_geom is None:
            self._base_geom = self.geometry()
            self._orig_font = QFont(self.font())

    def enterEvent(self, ev):
        super().enterEvent(ev)
        self._hovered = True
        f = QFont(self._orig_font)
        f.setPointSizeF(self._orig_font.pointSizeF() * 0.95)
        f.setBold(self._orig_font.bold())
        self.setFont(f)
        self._run_anim(scale=0.95)

    def leaveEvent(self, ev):
        super().leaveEvent(ev)
        self._hovered = False
        self.setFont(self._orig_font)
        self._run_anim(scale=1.0)

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        self._run_anim(scale=1.1)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        if self._hovered:
            f = QFont(self._orig_font)
            f.setPointSizeF(self._orig_font.pointSizeF() * 0.95)
            f.setBold(self._orig_font.bold())
            self.setFont(f)
            self._run_anim(scale=0.95)
        else:
            self.setFont(self._orig_font)
            self._run_anim(scale=1.0)

    def _run_anim(self, scale: float):
        if not self._base_geom:
            return
        base = self._base_geom
        w0, h0 = base.width(), base.height()
        cx = base.x() + w0 // 2
        cy = base.y() + h0 // 2
        new_w = int(w0 * scale)
        new_h = int(h0 * scale)
        new_x = cx - new_w // 2
        new_y = cy - new_h // 2
        end = QRect(new_x, new_y, new_w, new_h)
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(end)
        self._anim.start()


class ClickBounceButton(AnimatedButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._anim.setDuration(100)
        self._easing = QEasingCurve.OutBack

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        self._anim.setEasingCurve(QEasingCurve.InQuad)
        self._run_anim(scale=0.9)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        self._anim.setEasingCurve(self._easing)
        self._run_anim(scale=1.05)
        QTimer.singleShot(
            self._anim.duration(),
            lambda: (
                self._anim.setEasingCurve(QEasingCurve.OutQuad),
                self._run_anim(scale=1.0),
            ),
        )


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


COLOR_TAGS = {"gold": "#FFD700", "elixir": "#800080", "warn": "orange"}


def classify_colour(line: str) -> str:
    lo = line.lower()
    if "gold" in lo:
        return "gold"
    if "elixir" in lo:
        return "elixir"
    if "warn" in line.upper():
        return "warn"
    return "info"


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
        "enable_multi_account": False,
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


class WoodBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wood = QPixmap(os.path.join(BG, "BG.png"))

    def paintEvent(self, ev):
        painter = QPainter(self)
        if not self.wood.isNull():
            painter.drawTiledPixmap(self.rect(), self.wood)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 145))
        super().paintEvent(ev)


class LDInstancePickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select LDPlayer Instance")
        self.setModal(True)
        self.setFixedSize(520, 380)
        self.setStyleSheet("background:#1f1f1f;")
        self.index = None
        self.name = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)
        hdr = QLabel("Choose an LDPlayer instance")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet("color:#eaeaea; font-weight:600; font-size:15px;")
        self.layout.addWidget(hdr)
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "Action"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "\n            QTableWidget { background:#1a1a1a; color:#eaeaea; border:1px solid #333; }\n"
            "            QHeaderView::section { background:#222; color:#eaeaea; padding:6px; border:none; }\n"
            "            QTableWidget::item { background:#1a1a1a; }\n"
            "            QTableWidget::item:alternate { background:#202020; }\n"
            "            QTableWidget::item:selected { background:#2e2e2e; }\n        "
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        for c in range(3):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Fixed)
        self.layout.addWidget(self.table)
        self._equalize_columns()
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(
            "QPushButton{background:#444;color:#fff;border:none;border-radius:6px;padding:6px 12px;} "
            "QPushButton:hover{background:#666;}"
        )
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


class MainWindow(QMainWindow):
    update_available = pyqtSignal(str, str)

    def _apply_image_button(self, btn: QPushButton, filename: str, w: int, h: int):
        btn.setText("")
        btn.setFlat(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setIcon(QIcon(os.path.join(TEMPLATES_DIR, filename)))
        btn.setIconSize(QSize(w, h))
        btn.setFixedSize(w, h)
        btn.setStyleSheet("QPushButton{border:none;background:transparent;}")

    def _on_toggle_pause_play(self):
        if not self.paused:
            pause_bot()
            icon_play = QIcon(QPixmap(os.path.join(TEMPLATES_DIR, "play_button.png")))
            self._toggle_btn.setIcon(icon_play)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            if hasattr(self, "status_lbl"):
                self.status_lbl.setText("Status: Paused")
                self.status_lbl.setStyleSheet("color: #ff5252; padding-left: 8px;")
        else:
            resume_bot()
            icon_stop = QIcon(QPixmap(os.path.join(TEMPLATES_DIR, "stop_button.png")))
            self._toggle_btn.setIcon(icon_stop)
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            if hasattr(self, "status_lbl"):
                self.status_lbl.setText("Status: Working")
                self.status_lbl.setStyleSheet("color: #f0b64c; padding-left: 8px;")
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

    def _reload_village_icons(self):
        for idx, (cb, icon, apply_btn, save_btn) in enumerate(
            self.mv_village_widgets, start=1
        ):
            img_path = os.path.join(profiles_dir, f"account_{idx}.png")
            if os.path.isfile(img_path):
                pix = QPixmap(img_path)
                pix = pix.scaledToWidth(64, Qt.SmoothTransformation)
                icon.setPixmap(pix)
            else:
                icon.clear()

    def update_village_fade(self):
        multi_on = self.mv_enable_chk.isChecked()
        for idx, (cb, icon, apply_btn, save_btn) in enumerate(
            self.mv_village_widgets, start=1
        ):
            active = multi_on and cb.isChecked()
            cb.setEnabled(multi_on)
            apply_btn.setEnabled(active)
            save_btn.setEnabled(active)
            for w in [cb, icon, apply_btn, save_btn]:
                eff = QGraphicsOpacityEffect(icon)
                eff.setOpacity(1.0 if active else 0.35)
                icon.setGraphicsEffect(eff)

    def _save_village_config(self, idx: int):
        path = os.path.join(profiles_dir, f"Village_{idx}.json")
        if getattr(self, "active_village_idx", None) != idx or not os.path.exists(path):
            QMessageBox.warning(
                self,
                "Save Error",
                "Cannot save configuration: no configuration has been loaded for this village.",
            )
            return
        cfg = {
            "gold_threshold": int(self.gold_entry.text()),
            "elixir_threshold": int(self.elixir_entry.text()),
            "dark_elixir_threshold": int(self.dark_entry.text()),
            "upgrade_wall": self.upgrade_chk.isChecked(),
            "wall_gold_threshold": int(self.wall_gold_entry.text()),
            "wall_elixir_threshold": int(self.wall_elixir_entry.text()),
            "wall_level": int(self.wall_level_spin.value()),
            "request_troops": self.req_chk.isChecked(),
            "recipe_name": self.army_tab.get_active_name(),
            "train_mode": "smart",
            "quick_slot": 1,
        }
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
        QMessageBox.information(self, "Saved", f"Village_{idx} configuration saved!")

    def _load_village_config(self, idx: int):
        path = os.path.join(profiles_dir, f"Village_{idx}.json")
        if not os.path.exists(path):
            QMessageBox.warning(
                self, "Missing Config", f"No saved settings for Village_{idx}."
            )
            return
        with open(path, "r") as f:
            vcfg = json.load(f)
        self.gold_entry.setText(str(vcfg.get("gold_threshold", "")))
        self.elixir_entry.setText(str(vcfg.get("elixir_threshold", "")))
        self.dark_entry.setText(str(vcfg.get("dark_elixir_threshold", "")))
        self.upgrade_chk.setChecked(vcfg.get("upgrade_wall", False))
        self.wall_gold_entry.setText(str(vcfg.get("wall_gold_threshold", "")))
        self.wall_elixir_entry.setText(str(vcfg.get("wall_elixir_threshold", "")))
        self.wall_level_spin.setValue(vcfg.get("wall_level", 8))
        self.req_chk.setChecked(vcfg.get("request_troops", False))

    def _confirm_and_load(self, idx: int):
        reply = QMessageBox.question(
            self,
            "Confirm Load",
            f"Load configuration for Village_{idx}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            path = os.path.join(profiles_dir, f"Village_{idx}.json")
            if not os.path.exists(path):
                QMessageBox.warning(
                    self,
                    "Missing Config",
                    f"No saved settings for Village_{idx}.",
                )
                return
            self._load_village_config(idx)
            QMessageBox.information(
                self,
                "Loaded",
                f"Village_{idx} configuration loaded!",
            )
            self.active_village_idx = idx
            _, _, _, save_btn = self.mv_village_widgets[idx - 1]
            save_btn.setEnabled(True)

    def highlight_active_village(self, idx: int):
        for i, (cb, icon, btn, _) in enumerate(self.mv_village_widgets, start=1):
            if i == idx:
                cb.setStyleSheet("color: yellow; font-weight: bold;")
            else:
                cb.setStyleSheet(f"color: {self.mv_colors[i - 1]};")
        self.active_village_idx = idx
        self.stats_tab.current_village_idx = idx

    def _on_request_wizard(self, indices):
        run_village_wizard(indices, 0)
        bridge.wizardDone.emit()

    def _toggle_group(self, group: QGroupBox, enabled: bool):
        bg = "rgba(255,255,255,200)" if enabled else "rgba(80,80,80,150)"
        group.setStyleSheet(
            f"\n            QGroupBox {{\n                background: {bg};\n"
            "                border: 1px solid #FFFFFF;\n"
            "                border-radius: 4px;\n                margin-top: 6px;\n            }\n"
            "            QGroupBox::title {\n                subcontrol-origin: margin;\n"
            "                left: 8px; padding: 0 4px;\n            }\n        "
        )
        for w in group.findChildren((QLineEdit, QSpinBox)):
            w.setEnabled(enabled)

    def on_count_changed(self, n: int):
        multi_enabled = self.mv_enable_chk.isChecked()
        for idx, (cb, icon, apply_btn, save_btn) in enumerate(
            self.mv_village_widgets, start=1
        ):
            is_active = (idx <= n) and multi_enabled
            cb.setChecked(idx <= n)
            cb.setEnabled(is_active)
            apply_btn.setEnabled(is_active)
            save_btn.setEnabled(is_active)
            for w in [cb, icon, apply_btn, save_btn]:
                eff = QGraphicsOpacityEffect(w)
                eff.setOpacity(1.0 if is_active else 0.35)
                w.setGraphicsEffect(eff)
        self.update_village_fade()

    def _on_delete_all(self):
        ans = QMessageBox.question(
            self,
            "Delete Confirmation",
            "Do you want to delete **all** saved settings and images for **every** village?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        profiles = str(profiles_dir)
        for pattern in ["Village_*.json", "account_*.png"]:
            for path in glob.glob(os.path.join(profiles, pattern)):
                try:
                    os.remove(path)
                except OSError:
                    pass
        QMessageBox.information(
            self,
            "Deleted",
            "All village configurations and images have been removed.",
        )
        self.mv_enable_chk.setChecked(False)
        self.mv_count_spin.setValue(1)
        for cb, icon, apply_btn, save_btn in self.mv_village_widgets:
            cb.setChecked(False)
            cb.setEnabled(False)
            apply_btn.setEnabled(False)
            save_btn.setEnabled(False)
            icon.clear()

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
        self.setWindowTitle("MyBot(SIMPLICITY)   v3.50.0")
        self.host = None
        self.no_host = False
        self.resize(720, 620)
        self.setMinimumSize(640, 540)
        self.active_village_idx = None
        self._worker = None
        self.settings = load_settings()
        self.attack_images = {
            k: load_attack_assets(k) for k in ["Dragon_Attack", "ElectroDragon_Attack"]
        }
        hdrF = QFont("Segoe UI", 12, QFont.Bold)
        labF = QFont("Segoe UI", 10, QFont.Bold)

        central = WoodBackground()
        vroot = QVBoxLayout(central)
        vroot.setContentsMargins(0, 0, 0, 0)
        vroot.setSpacing(0)
        self.setCentralWidget(central)

        # 1. Header (Compact ~46px)
        header_bar = QWidget()
        header_bar.setFixedHeight(46)
        header_bar.setStyleSheet(
            "background: rgba(15, 15, 15, 230); border-bottom: 1px solid #333;"
        )
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(12, 4, 12, 4)
        header_layout.setSpacing(10)

        logo_lbl = QLabel()
        icon_path = os.path.join(TEMPLATES_DIR, "app_icon.ico")
        if os.path.exists(icon_path):
            logo_lbl.setPixmap(
                QPixmap(icon_path).scaled(
                    32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        header_layout.addWidget(logo_lbl)

        title_lbl = QLabel("SIMPLICITY v3.50")
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF; letter-spacing: 1px;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        sub_lbl = QLabel("Clash of Clans Automation")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet("color: #888888;")
        header_layout.addWidget(sub_lbl)
        vroot.addWidget(header_bar)

        # 2. QTabWidget - 7 horizontal tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background: rgba(22, 22, 22, 240);
                top: -1px;
            }
            QTabBar::tab {
                background: #252525;
                color: #b0b0b0;
                padding: 7px 14px;
                margin-right: 2px;
                border: 1px solid #3a3a3a;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                font-family: "Segoe UI", sans-serif;
                font-size: 11px;
                font-weight: bold;
                min-width: 70px;
            }
            QTabBar::tab:selected {
                background: #3a3a3a;
                color: #ffffff;
                border-color: #555555;
                border-bottom: 1px solid #3a3a3a;
            }
            QTabBar::tab:hover:!selected {
                background: #2f2f2f;
                color: #e0e0e0;
            }
            """
        )

        # ===== TAB 0: Logs tab =====
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.setContentsMargins(6, 6, 6, 6)
        logs_layout.setSpacing(4)

        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #333333;
                height: 4px;
            }
            QSplitter::handle:hover {
                background-color: #555555;
            }
            """
        )

        top_widget = QWidget()
        top_vbox = QVBoxLayout(top_widget)
        top_vbox.setContentsMargins(0, 0, 0, 0)
        top_vbox.setSpacing(2)
        top_label = QLabel("BOT LOG")
        top_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        top_label.setStyleSheet(
            "color: #EFE2BA; background: transparent; padding-left: 2px;"
        )
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setStyleSheet(
            "background: #141414; color: #EFE2BA; border: 1px solid #333333;"
        )
        top_vbox.addWidget(top_label)
        top_vbox.addWidget(self.log)

        bot_widget = QWidget()
        bot_vbox = QVBoxLayout(bot_widget)
        bot_vbox.setContentsMargins(0, 0, 0, 0)
        bot_vbox.setSpacing(2)
        bot_label = QLabel("ATTACK LOG")
        bot_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        bot_label.setStyleSheet(
            "color: #FFD700; background: transparent; padding-left: 2px;"
        )
        self.attack_log = QTextEdit()
        self.attack_log.setReadOnly(True)
        self.attack_log.setFont(QFont("Consolas", 9))
        self.attack_log.setStyleSheet(
            "background: #141414; color: #EFE2BA; border: 1px solid #333333;"
        )
        bot_vbox.addWidget(bot_label)
        bot_vbox.addWidget(self.attack_log)

        splitter.addWidget(top_widget)
        splitter.addWidget(bot_widget)
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)
        splitter.setSizes([380, 200])
        logs_layout.addWidget(splitter)

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
        header_container = QWidget()
        header_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        left_lbl = QLabel()
        pix_left = QPixmap(os.path.join(TEMPLATES_DIR, "icon_siege.png"))
        if not pix_left.isNull():
            pix_left = pix_left.scaledToWidth(50, Qt.SmoothTransformation)
            left_lbl.setPixmap(pix_left)
            left_lbl.setFixedSize(pix_left.size())
            left_eff = QGraphicsOpacityEffect(left_lbl)
            left_eff.setOpacity(0.7)
            left_lbl.setGraphicsEffect(left_eff)
        header_layout.addWidget(left_lbl)
        header_layout.addStretch()

        mid_lbl = QLabel()
        pix_mid_orig = QPixmap(os.path.join(TEMPLATES_DIR, "icon_attack_criteria.png"))
        if not pix_mid_orig.isNull():
            pix_mid = pix_mid_orig.scaledToWidth(180, Qt.SmoothTransformation)
            mid_lbl.setPixmap(pix_mid)
            mid_lbl.setFixedSize(pix_mid.size())
        header_layout.addWidget(mid_lbl)
        header_layout.addStretch()

        right_lbl = QLabel()
        pix_right = QPixmap(os.path.join(TEMPLATES_DIR, "icon_dragon.png"))
        if not pix_right.isNull():
            pix_right = pix_right.scaledToWidth(50, Qt.SmoothTransformation)
            right_lbl.setPixmap(pix_right)
            right_lbl.setFixedSize(pix_right.size())
            right_eff = QGraphicsOpacityEffect(right_lbl)
            right_eff.setOpacity(0.7)
            right_lbl.setGraphicsEffect(right_eff)
        header_layout.addWidget(right_lbl)

        grid.addWidget(header_container, row, 0, 1, 2)
        row += 1
        grid.addWidget(line(), row, 0, 1, 2)
        row += 1

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
        lbl_gold.setStyleSheet("color:#FFFFFF;")
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
        lbl_elixir.setStyleSheet("color:#FFFFFF;")
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
        lbl_de.setStyleSheet("color:#FFFFFF;")
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
        self.upgrade_chk.setStyleSheet("color:#FFFFFF;")
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
        lbl_wg_gold.setStyleSheet("color:#FFFFFF;")
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
        lbl_wg_elixir.setStyleSheet("color:#FFFFFF;")
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
        lbl_wl.setStyleSheet("color:#FFFFFF;")
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
        self.req_chk.setStyleSheet("color:#FFFFFF;")
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
        self.army_tab.recipe_changed.connect(self._on_army_recipe_changed)

        # ===== TAB 3: Multi-Village tab =====
        multi_tab = QWidget()
        mv_layout = QVBoxLayout(multi_tab)
        mv_layout.setContentsMargins(10, 8, 10, 8)
        mv_layout.setSpacing(8)
        mv_layout.setAlignment(Qt.AlignTop)

        mv_enable_container = QWidget()
        mv_enable_layout = QHBoxLayout(mv_enable_container)
        mv_enable_layout.setContentsMargins(0, 0, 0, 0)
        mv_enable_layout.setSpacing(6)
        self.mv_enable_chk = QCheckBox("Enable Multi-Village")
        self.mv_enable_chk.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.mv_enable_chk.setStyleSheet("color: #FFFFFF;")
        self.mv_enable_chk.setChecked(self.settings.get("enable_multi_village", False))
        mv_enable_layout.addWidget(self.mv_enable_chk)
        icon_switch_lbl = QLabel()
        pix_switch = QPixmap(
            os.path.join(TEMPLATES_DIR, "icon_switch.png")
        ).scaledToWidth(36, Qt.SmoothTransformation)
        icon_switch_lbl.setPixmap(pix_switch)
        mv_enable_layout.addWidget(icon_switch_lbl)
        mv_enable_layout.addStretch()
        mv_layout.addWidget(mv_enable_container, 0, Qt.AlignTop)

        h1 = QHBoxLayout()
        lbl_accounts = QLabel("How many accounts?")
        lbl_accounts.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_accounts.setStyleSheet("color: #FFFFFF;")
        h1.addWidget(lbl_accounts)
        self.mv_count_spin = QSpinBox()
        self.mv_count_spin.setRange(2, 5)
        self.mv_count_spin.setValue(2)
        self.mv_count_spin.setFont(QFont("Segoe UI", 11, QFont.Bold))
        h1.addWidget(self.mv_count_spin)
        mv_layout.addLayout(h1)

        h2 = QHBoxLayout()
        lbl_interval = QLabel("Switch interval:")
        lbl_interval.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_interval.setStyleSheet("color: #FFFFFF;")
        h2.addWidget(lbl_interval)
        self.mv_interval = QComboBox()
        self.mv_interval.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.mv_interval.addItems(["30 minutes", "1 hour", "1.5 hours", "2 hours"])
        h2.addWidget(self.mv_interval)
        mv_layout.addLayout(h2)

        self.delete_btn = AnimatedButton("Delete All")
        self.delete_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.delete_btn.setFixedSize(95, 26)
        self.delete_btn.setStyleSheet(
            "\n            QPushButton {\n                background: qlineargradient(\n"
            "                    x1:0,y1:0, x2:0,y2:1,\n"
            "                    stop:0 #FF5252, stop:1 #D32F2F\n"
            "                );\n                color: #FFF;\n                border: none;\n"
            "                border-radius: 6px;\n            }\n"
            "            QPushButton:hover { background: #FF867C; }\n        "
        )
        self.delete_btn.clicked.connect(self._on_delete_all)
        mv_layout.addWidget(self.delete_btn, alignment=Qt.AlignRight)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)
        group = QGroupBox("Villages")
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        group.setStyleSheet(
            "\n            QGroupBox {\n                color: #FFFFFF;\n"
            "                border: 1px solid #EFE2BA;\n                margin-top: 6px;\n            }\n"
            "            QGroupBox::title {\n                subcontrol-origin: margin;\n"
            "                left: 8px; padding: 0 4px;\n            }\n        "
        )
        self.mv_village_widgets = []
        colors = ["#eaecee", "#eaecee", "#eaecee", "#eaecee", "#eaecee"]
        self.mv_colors = colors
        for i in range(1, 6):
            row_lay = QHBoxLayout()
            cb = QCheckBox(f"Village_{i}")
            cb.setFont(QFont("Segoe UI", 10, QFont.Bold))
            cb.setStyleSheet(f"color: {colors[i - 1]};")
            pix_acc = QPixmap(os.path.join(profiles_dir, f"account_{i}.png"))
            icon = QLabel()
            icon.setFixedWidth(64)
            icon.setFixedHeight(38)
            if not pix_acc.isNull():
                icon.setPixmap(pix_acc.scaledToWidth(64, Qt.SmoothTransformation))
            row_lay.addWidget(cb)
            row_lay.addWidget(icon)
            apply_btn = AnimatedButton("Load")
            apply_btn.setFont(QFont("Segoe UI", 8, QFont.Bold))
            apply_btn.setStyleSheet(
                "\n                QPushButton {\n"
                "                    background: qlineargradient(\n"
                "                        x1:0, y1:0, x2:0, y2:1,\n"
                "                        stop:0 #4CAF50,\n"
                "                        stop:1 #388E3C\n"
                "                    );\n                    color: #FFFFFF;\n"
                "                    border: none;\n                    border-radius: 5px;\n"
                "                    padding: 4px 14px;\n                }\n"
                "                QPushButton:hover {\n"
                "                    background: qlineargradient(\n"
                "                        x1:0, y1:0, x2:0, y2:1,\n"
                "                        stop:0 #66BB6A,\n"
                "                        stop:1 #4CAF50\n                    );\n                }\n            "
            )
            row_lay.addWidget(apply_btn)
            save_btn = AnimatedButton("Save")
            save_btn.setFont(QFont("Segoe UI", 8, QFont.Bold))
            save_btn.setStyleSheet(
                "\n                QPushButton {\n"
                "                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,\n"
                "                        stop:0 #2196F3, stop:1 #1976D2);\n"
                "                    color: #FFF; border:none; border-radius:5px;\n"
                "                    padding:4px 14px;\n                }\n"
                "                QPushButton:hover {\n                    background: #42A5F5;\n                }\n            "
            )
            row_lay.addWidget(save_btn)
            row_lay.addStretch()
            vbox.addLayout(row_lay)
            self.mv_village_widgets.append((cb, icon, apply_btn, save_btn))
            apply_btn.setEnabled(False)
            cb.toggled.connect(lambda checked, b=apply_btn: b.setEnabled(checked))
            apply_btn.clicked.connect(lambda _, idx=i: self._confirm_and_load(idx))
            save_btn.setEnabled(True)
            save_btn.clicked.connect(
                lambda _, village_idx=i: self._save_village_config(village_idx)
            )
        group.setLayout(vbox)
        mv_layout.addWidget(group, 1)

        bridge.setActiveVillage.connect(self.highlight_active_village)
        for cb, icon, apply_btn, save_btn in self.mv_village_widgets:
            cb.setEnabled(False)
            apply_btn.setEnabled(False)
            save_btn.setEnabled(True)
            for w in [icon, apply_btn]:
                eff = QGraphicsOpacityEffect(w)
                eff.setOpacity(0.35)
                w.setGraphicsEffect(eff)

        def apply_mv_state():
            enabled = self.mv_enable_chk.isChecked()
            self.mv_count_spin.setEnabled(enabled)
            self.mv_interval.setEnabled(enabled)
            for cb, icon, apply_btn, save_btn in self.mv_village_widgets:
                active = enabled and cb.isChecked()
                cb.setEnabled(active)
                apply_btn.setEnabled(active)
                if active:
                    apply_btn.graphicsEffect().setOpacity(1.0)
                    icon.graphicsEffect().setOpacity(1.0)
                else:
                    apply_btn.graphicsEffect().setOpacity(0.35)
                    icon.graphicsEffect().setOpacity(0.35)
            self.on_count_changed(self.mv_count_spin.value())

        self.mv_count_spin.valueChanged.connect(self.on_count_changed)
        self.mv_enable_chk.toggled.connect(lambda _: apply_mv_state())
        apply_mv_state()
        self.on_count_changed(self.mv_count_spin.value())
        self.mv_enable_chk.toggled.connect(self.update_village_fade)
        self.mv_count_spin.valueChanged.connect(self.update_village_fade)
        self.update_village_fade()

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
        self.clan_games_toggle.setStyleSheet("color: #FFFFFF;")
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
        self.clan_capital_toggle.setStyleSheet("color:#FFFFFF;")
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
            "so Simplicity can detect the Clan Capital boat more reliably."
        )
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet(
            "\n            color: #FFFFFF;\n            font-size: 13px;\n"
            "            font-weight: 600;\n            margin-top: 4px;\n        "
        )
        cc_layout.addWidget(note_lbl)

        cc_lvl_row = QWidget()
        cc_lvl_h = QHBoxLayout(cc_lvl_row)
        cc_lvl_h.setContentsMargins(0, 0, 0, 0)
        cc_lvl_h.setSpacing(8)
        lvl_label = QLabel("Capital Hall level:")
        lvl_label.setStyleSheet("color:#FFFFFF; font-size:15px; font-weight:600;")
        cc_lvl_h.addWidget(lvl_label, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.cc_level = QSpinBox()
        self.cc_level.setRange(1, 10)
        self.cc_level.setSingleStep(1)
        self.cc_level.setValue(int(self.settings.get("capital_hall_level", 9)))
        self.cc_level.setToolTip("Select your Clan Capital Hall level (1–10).")
        self.cc_level.setFixedSize(90, 34)
        self.cc_level.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        self.cc_level.setStyleSheet(
            "\n            QSpinBox {\n                color: #111111;\n"
            "                background: #FFFFFF;\n                padding: 4px 8px;\n"
            "                border: 1px solid rgba(255,255,255,0.30);\n"
            "                border-radius: 6px;\n            }\n"
            "            QSpinBox::up-button, QSpinBox::down-button {\n"
            "                width: 16px; height: 16px;\n                margin: 1px;\n            }\n"
            "            QSpinBox:disabled {\n"
            "                color: rgba(255,255,255,0.45);\n"
            "                background: rgba(255,255,255,0.12);\n"
            "                border: 1px solid rgba(255,255,255,0.12);\n            }\n        "
        )
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
            multi_village_cb=self.mv_enable_chk,
            parent=self,
        )
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats_from_json)
        self._stats_timer.start(5000)

        # ===== TAB 7: Debug tab (Crop Tool) =====
        self.debug_tab = DebugTab()

        # Add tabs in order (Log at index 0)
        self.tab_widget.addTab(logs_tab, "Log")
        self.tab_widget.addTab(gen_tab, "General")
        self.tab_widget.addTab(self.army_tab, "Army")
        self.tab_widget.addTab(multi_tab, "Multi-Village")
        self.tab_widget.addTab(clan_tab, "Clan Games")
        self.tab_widget.addTab(cc_tab, "Clan Capital")
        self.tab_widget.addTab(self.stats_tab, "Statistics")
        self.tab_widget.addTab(self.debug_tab, "Debug")
        self.tab_widget.setCurrentIndex(0)

        vroot.addWidget(self.tab_widget, 1)

        # ===== Log stream =====
        self.stream = TimestampStream()
        self.stream.new_line.connect(self._append_log)
        sys.stdout = self.stream
        sys.stderr = self.stream

        # ===== Bottom Bar (Fixed) =====
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(64)
        bottom_bar.setStyleSheet(
            "background: rgba(22, 22, 22, 230); border-top: 1px solid #333333;"
        )
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12, 6, 12, 6)
        bottom_layout.setSpacing(10)

        self.start_btn = ClickBounceButton()
        self.start_btn.setObjectName("startBtn")
        self._apply_image_button(self.start_btn, "start.png", 140, 50)

        self.stop_btn = ClickBounceButton()
        self.stop_btn.setObjectName("endBtn")
        self._apply_image_button(self.stop_btn, "end.png", 140, 50)
        self.stop_btn.setEnabled(False)

        self._toggle_btn = ClickBounceButton()
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setIcon(QIcon(os.path.join(TEMPLATES_DIR, "stop_button.png")))
        self._toggle_btn.setIconSize(QSize(36, 36))
        self._toggle_btn.setFixedSize(44, 44)
        self._toggle_btn.setStyleSheet(
            "QPushButton { background: #2e2e2e; border: 1px solid #444; border-radius: 6px; } "
            "QPushButton:hover { background: #3d3d3d; border-color: #666; }"
        )
        self.paused = False
        self._toggle_btn.clicked.connect(self._on_toggle_pause_play)

        self.status_lbl = QLabel("Status: Ready")
        self.status_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.status_lbl.setStyleSheet("color: #60d394; padding-left: 8px;")

        version_lbl = QLabel("v3.50.0")
        version_lbl.setFont(QFont("Segoe UI", 9))
        version_lbl.setStyleSheet("color: #888888; padding-right: 4px;")

        bottom_layout.addWidget(self.start_btn)
        bottom_layout.addWidget(self.stop_btn)
        bottom_layout.addWidget(self._toggle_btn)
        bottom_layout.addWidget(self.status_lbl)
        bottom_layout.addStretch()
        bottom_layout.addWidget(version_lbl)

        vroot.addWidget(bottom_bar)

        bridge.requestWizard.connect(self._on_request_wizard)
        bridge.wizardDone.connect(self._reload_village_icons)
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn.clicked.connect(self.on_end)

        self._warned = False
        self.updater = Updater(self)
        self.updater.update_available.connect(self.on_update_available)
        QTimer.singleShot(500, self.updater.check_for_update)

    def _lbl(self, text: str, colour: str, font: QFont):
        lbl = QLabel(text)
        font.setBold(True)
        lbl.setFont(font)
        lbl.setStyleSheet(
            f"\n            color: {colour};\n            border: 1px solid #FFFFFF;\n"
            "            background: rgba(0,0,0,120);\n            padding: 2px 4px;\n        "
        )
        shadow = QGraphicsDropShadowEffect(lbl)
        shadow.setBlurRadius(6)
        shadow.setOffset(1, 1)
        shadow.setColor(QColor(0, 0, 0, 180))
        lbl.setGraphicsEffect(shadow)
        return lbl

    def _on_army_recipe_changed(self):
        name = self.army_tab.get_active_name()
        print(f"[ARMY] Recipe changed: {name}")

    def _toggle_wall_inputs(self, enabled: bool):
        policy = Qt.StrongFocus if enabled else Qt.NoFocus
        for w in [self.wall_gold_entry, self.wall_elixir_entry, self.wall_level_spin]:
            w.setEnabled(enabled)
            w.setFocusPolicy(policy)

    def _append_log(self, line: str):
        colour = COLOR_TAGS.get(classify_colour(line), "info")
        html_line = f"<span class='{colour}'>{line}</span><br>"
        lo = line.lower()
        attack_keywords = ("attack", "loot", "star", "destroy", "gain")
        if any(kw in lo for kw in attack_keywords):
            if hasattr(self, "attack_log") and self.attack_log is not None:
                self.attack_log.moveCursor(QTextCursor.End)
                self.attack_log.insertHtml(html_line)
                self.attack_log.moveCursor(QTextCursor.End)
                return

        self.log.moveCursor(QTextCursor.End)
        self.log.insertHtml(html_line)
        self.log.moveCursor(QTextCursor.End)

    def on_start(self):
        if self._worker and self._worker.is_alive():
            return
        emu = self.choose_emulator()
        if emu is None and not getattr(main, "emulator_key", None):
            print("[INFO] Start aborted (no emulator selected).")
            return
        try:
            if emu:
                owns_lock = (
                    hasattr(self, "_emu_socket") and self._emu_socket.fileno() != -1
                )
                if not owns_lock:
                    port_map = {MEMU: 6200, BLUESTACKS: 6201, LDPLAYER: 6202}
                    if getattr(main, "emulator_key", "") == "ldplayer_multi":
                        port = 6202 + int(getattr(main, "ld_index", 0))
                    else:
                        port = port_map.get(self.host, 6299)
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if sys.platform == "win32":
                        test_sock.setsockopt(
                            socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
                        )
                    test_sock.bind(("127.0.0.1", port))
                    self._emu_socket = test_sock
                    atexit.register(self._emu_socket.close)
            print(f"[INFO] Using emulator: {emu}")
            cfg = self._collect_cfg()
            cfg["stats"] = {}
            main.stop_event.clear()
            self._worker = QtThreadCompat(
                target=main.bot_loop, args=(cfg,), parent=self
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
                "Close that bot and press Start again, or restart this bot and choose a different emulator.",
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
                if not self._worker.wait(3000):
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
            icon_stop = QIcon(QPixmap(os.path.join(TEMPLATES_DIR, "stop_button.png")))
            self._toggle_btn.setIcon(icon_stop)

        if hasattr(self, "status_lbl"):
            self.status_lbl.setText("Status: Ready")
            self.status_lbl.setStyleSheet("color: #60d394; padding-left: 8px;")

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
            self.mv_enable_chk,
            self.mv_count_spin,
            self.mv_interval,
            self.delete_btn,
        ]:
            w.setEnabled(en)
        for cb, icon, apply_btn, save_btn in self.mv_village_widgets:
            apply_btn.setEnabled(en and apply_btn.isEnabled())
            save_btn.setEnabled(en and save_btn.isEnabled())
            cb.setEnabled(en and cb.isEnabled())

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
            "train_mode": "smart",
            "quick_slot": 1,
            "enable_clan_games": self.clan_games_toggle.isChecked(),
            "enable_clan_capital": self.clan_capital_toggle.isChecked(),
            "capital_hall_level": int(self.cc_level.value()),
            "enable_stats": self.stats_tab.enable_stats_chk.isChecked(),
            "enable_multi_account": self.mv_enable_chk.isChecked(),
            "multi_count": self.mv_count_spin.value(),
            "multi_interval_mins": {
                "30 minutes": 30, "1 hour": 60, "1.5 hours": 90, "2 hours": 120,
            }[self.mv_interval.currentText()],
            "selected_villages": [
                idx for idx, (cb, icon, apply_btn, _) in enumerate(self.mv_village_widgets, start=1)
                if cb.isChecked()
            ],
            "current_village_idx": 1,
        }
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
    app.setStyleSheet(
        "\n    QLineEdit, QSpinBox, QComboBox, QTextEdit {\n"
        "        background: rgba(255,255,255,200);\n"
        "        border: 1px solid #5D4037;\n        border-radius: 4px;\n    }\n"
        "    QPushButton {\n        background: rgba(100, 100, 100, 200);\n"
        "        border: 1px solid #4E342E;\n    }\n"
        "    QPushButton:hover {\n        background: rgba(120,120,120,200);\n    }\n\n"
        "    QPushButton#startBtn,\n    QPushButton#endBtn {\n"
        "        background: transparent;\n        border: none;\n"
        "        padding: 0;\n    }\n\n"
        "    QPushButton#startBtn:hover,\n    QPushButton#endBtn:hover,\n"
        "    QPushButton#startBtn:disabled,\n    QPushButton#endBtn:disabled {\n"
        "        background: transparent;\n        border: none;\n    }\n\n"
        "    QPushButton#startBtn:pressed,\n    QPushButton#endBtn:pressed {\n"
        "        background: transparent;\n        border: none;\n"
        "        padding-top: 1px;\n    }\n\n\n    "
    )
    zero_all_stats_files()
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
