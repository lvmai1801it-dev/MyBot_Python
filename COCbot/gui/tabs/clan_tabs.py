# ==== COCbot/gui/tabs/clan_tabs.py ====
"""Clan Games / Clan Capital tab widget builder."""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from COCbot.gui.constants import TEMPLATES_DIR


def build_clan_tabs(win):
    # ===== TAB 4: Clan Games tab =====
    clan_tab = QWidget()
    cg_page = QVBoxLayout(clan_tab)
    cg_page.setContentsMargins(0, 10, 0, 10)
    cg_page.setSpacing(10)

    cg_card = QFrame()
    cg_card.setObjectName("card")
    cg_box = QVBoxLayout(cg_card)
    cg_box.setContentsMargins(14, 12, 14, 12)
    cg_box.setSpacing(8)
    cg_head = QHBoxLayout()
    cg_head.setSpacing(8)
    cg_title = QLabel("Clan Games")
    cg_title.setStyleSheet("font-size:13px; font-weight:600; color:#193431;")
    cg_head.addWidget(cg_title)
    cg_head.addStretch()
    cg_icon = QLabel()
    cg_icon_path = os.path.join(TEMPLATES_DIR, "icon_games.png")
    if os.path.exists(cg_icon_path):
        pix_cg_icon = QPixmap(cg_icon_path)
        if not pix_cg_icon.isNull():
            cg_icon.setPixmap(pix_cg_icon.scaled(
                36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    cg_head.addWidget(cg_icon)
    cg_box.addLayout(cg_head)

    win.clan_games_toggle = QCheckBox("Enable Clan Games")
    win.clan_games_toggle.setChecked(
        win.settings.get("enable_clan_games", False))
    cg_box.addWidget(win.clan_games_toggle)

    cg_desc = QLabel(
        "Tự động mở Events, nhận thưởng và làm nhiệm vụ Clan Games. "
        "Bật trước khi mùa Clan Games bắt đầu để bot chạy đúng lịch.")
    cg_desc.setWordWrap(True)
    cg_desc.setStyleSheet("font-size:10px; color:#657877;")
    cg_box.addWidget(cg_desc)
    cg_page.addWidget(cg_card)

    cg_tips = QFrame()
    cg_tips.setObjectName("card")
    tips_box = QVBoxLayout(cg_tips)
    tips_box.setContentsMargins(14, 12, 14, 12)
    tips_box.setSpacing(6)
    tips_title = QLabel("Cách hoạt động")
    tips_title.setStyleSheet(
        "font-size:12px; font-weight:600; color:#193431;")
    tips_box.addWidget(tips_title)
    for line in (
        "Mở tab Events và nhận thưởng khi có sẵn.",
        "Tự làm nhiệm vụ Clan Games trong lúc farm.",
        "Nên bật trước khi mùa mới bắt đầu.",
    ):
        bullet = QLabel(f"•  {line}")
        bullet.setWordWrap(True)
        bullet.setStyleSheet("font-size:10px; color:#657877;")
        tips_box.addWidget(bullet)
    cg_page.addWidget(cg_tips)
    cg_page.addStretch()

    # ===== TAB 5: Clan Capital tab =====
    cc_tab = QWidget()
    cc_page = QVBoxLayout(cc_tab)
    cc_page.setContentsMargins(0, 10, 0, 10)
    cc_page.setSpacing(10)

    cc_card = QFrame()
    cc_card.setObjectName("card")
    cc_box = QVBoxLayout(cc_card)
    cc_box.setContentsMargins(14, 12, 14, 12)
    cc_box.setSpacing(8)
    cc_head = QHBoxLayout()
    cc_head.setSpacing(8)
    cc_title = QLabel("Clan Capital")
    cc_title.setStyleSheet("font-size:13px; font-weight:600; color:#193431;")
    cc_head.addWidget(cc_title)
    cc_head.addStretch()
    cc_icon = QLabel()
    cc_icon_path = os.path.join(TEMPLATES_DIR, "clan_capital_logo.png")
    if os.path.exists(cc_icon_path):
        pix_cc_icon = QPixmap(cc_icon_path)
        if not pix_cc_icon.isNull():
            cc_icon.setPixmap(pix_cc_icon.scaled(
                36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    cc_head.addWidget(cc_icon)
    cc_box.addLayout(cc_head)

    win.clan_capital_toggle = QCheckBox("Enable Clan Capital")
    win.clan_capital_toggle.setChecked(
        win.settings.get("enable_clan_capital", False))
    cc_box.addWidget(win.clan_capital_toggle)

    note_lbl = QLabel(
        "Dùng scenery mặc định để bot nhận diện thuyền Clan Capital "
        "ổn định hơn.")
    note_lbl.setWordWrap(True)
    note_lbl.setStyleSheet("font-size:10px; color:#657877;")
    cc_box.addWidget(note_lbl)

    cc_lvl_row = QHBoxLayout()
    cc_lvl_row.setSpacing(8)
    lvl_label = QLabel("Capital Hall level")
    lvl_label.setStyleSheet("font-size:11px; color:#193431;")
    cc_lvl_row.addWidget(lvl_label)
    win.cc_level = QSpinBox()
    win.cc_level.setRange(1, 10)
    win.cc_level.setSingleStep(1)
    win.cc_level.setValue(int(win.settings.get("capital_hall_level", 9)))
    win.cc_level.setToolTip("Select your Clan Capital Hall level (1-10).")
    win.cc_level.setFixedSize(90, 28)
    win.cc_level.setFont(QFont("Segoe UI", 11))
    cc_lvl_row.addWidget(win.cc_level)
    cc_lvl_row.addStretch()
    cc_box.addLayout(cc_lvl_row)
    cc_page.addWidget(cc_card)
    cc_page.addStretch()

    def _cc_toggle_update(on: bool):
        note_lbl.setEnabled(on)
        lvl_label.setEnabled(on)
        win.cc_level.setEnabled(on)

    _cc_toggle_update(win.clan_capital_toggle.isChecked())
    win.clan_capital_toggle.toggled.connect(_cc_toggle_update)
    return clan_tab, cc_tab
