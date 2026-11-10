# ==== COCbot/gui/tabs/log_tab.py ====
"""Log tab widget builder."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


def build_logs_tab(win):
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
    bot_title.setStyleSheet("font-size:12px; font-weight:600; color:#193431;")
    bot_head.addWidget(bot_title)
    bot_head.addStretch()
    win.log_filter = QComboBox()
    win.log_filter.addItems(["All events", "INFO", "SUCCESS", "WARNING", "ERROR"])
    win.log_filter.setFixedWidth(96)
    win.log_filter.currentTextChanged.connect(win._on_log_filter_changed)
    bot_head.addWidget(win.log_filter)
    export_btn = QPushButton("Export")
    export_btn.setFixedHeight(24)
    export_btn.clicked.connect(win._export_log)
    bot_head.addWidget(export_btn)
    bot_card_v.addLayout(bot_head)

    win.log_table = QTableWidget(0, 3)
    win.log_table.setHorizontalHeaderLabels(["TIME", "LEVEL", "EVENT"])
    win.log_table.verticalHeader().setVisible(False)
    win.log_table.setShowGrid(False)
    win.log_table.setAlternatingRowColors(True)
    win.log_table.setWordWrap(False)
    win.log_table.setTextElideMode(Qt.ElideRight)
    win.log_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    win.log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    win.log_table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.Fixed)
    win.log_table.setColumnWidth(0, 66)
    win.log_table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.Fixed)
    win.log_table.setColumnWidth(1, 64)
    win.log_table.horizontalHeader().setSectionResizeMode(
        2, QHeaderView.Stretch)
    win.log_table.verticalHeader().setDefaultSectionSize(24)
    win.log_table.setMinimumHeight(240)
    bot_card_v.addWidget(win.log_table, 1)

    bot_foot = QHBoxLayout()
    bot_foot.setSpacing(6)
    win.auto_scroll_chk = QCheckBox("Auto-scroll")
    win.auto_scroll_chk.setChecked(True)
    bot_foot.addWidget(win.auto_scroll_chk)
    bot_foot.addStretch()
    win.log_count_lbl = QLabel("0 events · All systems ready")
    win.log_count_lbl.setStyleSheet("color:#657877; font-size:10px;")
    bot_foot.addWidget(win.log_count_lbl)
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
    atk_title.setStyleSheet("font-size:12px; font-weight:600; color:#193431;")
    atk_head.addWidget(atk_title)
    win.attack_count_lbl = QLabel("0")
    win.attack_count_lbl.setStyleSheet(
        "background:#EEF2F6; color:#536D80; border-radius:3px;"
        " padding:1px 5px; font-size:8px; font-weight:600;")
    atk_head.addWidget(win.attack_count_lbl)
    atk_head.addStretch()
    atk_sub = QLabel("This session")
    atk_sub.setStyleSheet("color:#657877; font-size:10px;")
    atk_head.addWidget(atk_sub)
    atk_v.addLayout(atk_head)

    win.attack_table = QTableWidget(0, 7)
    win.attack_table.setHorizontalHeaderLabels(
        ["TIME", "MODE", "GOLD", "ELIXIR", "DARK", "TROPHIES", "BONUS"])
    win.attack_table.verticalHeader().setVisible(False)
    win.attack_table.setShowGrid(False)
    win.attack_table.setAlternatingRowColors(True)
    win.attack_table.setWordWrap(False)
    win.attack_table.setTextElideMode(Qt.ElideRight)
    win.attack_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    win.attack_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    win.attack_table.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch)
    win.attack_table.verticalHeader().setDefaultSectionSize(22)
    win.attack_table.setMinimumHeight(100)
    atk_v.addWidget(win.attack_table, 1)
    win._reset_attack_table()
    logs_layout.addWidget(atk_card, 35)
    return logs_tab
