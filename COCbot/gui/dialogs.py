# ==== COCbot/gui/dialogs.py ====
"""Emulator / LDPlayer selection dialogs."""
import os

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
)
from PyQt5.QtCore import QVariantAnimation

from COCbot.emulator.ldplayer import list_ld_instances
from COCbot.gui.constants import TEMPLATES_DIR


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
