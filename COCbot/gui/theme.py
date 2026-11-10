"""Light UI theme matching the new MyBot design.

Palette and component sizes follow the Figma spec:
- window 480x670, light background, dark teal title bar
- white cards, 1px #DCE5E1 borders, 6px radius
- primary #13775F, muted #657877
"""

from __future__ import annotations

from pathlib import Path

from COCbot.app.paths import TEMPLATE_DIR

_CHECK_ICON = (Path(TEMPLATE_DIR) / "ui_check.png").as_posix()
_RADIO_ICON = (Path(TEMPLATE_DIR) / "ui_radio.png").as_posix()

# Palette
BG = "#F2F5F3"
TITLE_BG = "#142C2B"
CARD = "#FFFFFF"
TEXT = "#193431"
TEXT_MUTED = "#657877"
PRIMARY = "#13775F"
PRIMARY_HOVER = "#0F6450"
BORDER = "#DCE5E1"
TABLE_HEADER = "#F5F7F6"
TAB_ACTIVE = "#EAF3EE"
INFO_BG = "#EEF2F6"
INFO_TEXT = "#536D80"
SUCCESS_BG = "#E8F4EC"
SUCCESS_TEXT = "#13775F"
WARNING_BG = "#FFF6E5"
WARNING_TEXT = "#9A6B00"
ERROR_BG = "#FFF3F1"
ERROR_TEXT = "#A82921"
STOP_BG = "#FFF3F1"
STOP_TEXT = "#A82921"
STOP_BORDER = "#D9A199"

GLOBAL_QSS = f"""
* {{
    font-family: "Segoe UI", "Arial", sans-serif;
    outline: none;
}}
QWidget {{
    color: {TEXT};
    background: transparent;
    selection-background-color: {TAB_ACTIVE};
    selection-color: {TEXT};
    font-size: 11px;
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QLabel {{
    background: transparent;
}}
QLabel#muted {{
    color: {TEXT_MUTED};
}}
QLabel#appTitle {{
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 600;
}}
QLabel#appSub {{
    color: #BFD3CE;
    font-size: 10px;
    font-weight: 500;
}}
QLabel#appBadge {{
    color: #BFD3CE;
    font-size: 10px;
    font-weight: 400;
}}
QLabel#cardTitle {{
    color: {TEXT};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#cardSub {{
    color: {TEXT_MUTED};
    font-size: 10px;
}}
QToolTip {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px 8px;
    border-radius: 4px;
}}

/* ---------- Inputs ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 22px;
    selection-background-color: {TAB_ACTIVE};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {PRIMARY};
}}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
    color: #A3B3AF;
    background: {TABLE_HEADER};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {TAB_ACTIVE};
    selection-color: {TEXT};
    outline: none;
}}

/* ---------- Buttons ---------- */
QPushButton {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 500;
    min-height: 28px;
}}
QPushButton:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
}}
QPushButton:pressed {{
    background: {TABLE_HEADER};
}}
QPushButton:disabled {{
    color: #A3B3AF;
    border-color: {BORDER};
    background: {TABLE_HEADER};
}}
QPushButton#primaryBtn {{
    background: {PRIMARY};
    color: #FFFFFF;
    border: 1px solid {PRIMARY};
    font-weight: 600;
}}
QPushButton#primaryBtn:hover {{
    background: {PRIMARY_HOVER};
    border-color: {PRIMARY_HOVER};
    color: #FFFFFF;
}}
QPushButton#primaryBtn:disabled {{
    background: #9CC4BA;
    border-color: #9CC4BA;
    color: #F2F5F3;
}}
QPushButton#stopBtn {{
    background: {STOP_BG};
    color: {STOP_TEXT};
    border: 1px solid {STOP_BORDER};
}}
QPushButton#stopBtn:hover {{
    background: #FFE8E4;
    color: {STOP_TEXT};
    border-color: {STOP_TEXT};
}}
QPushButton#stopBtn:disabled {{
    background: {TABLE_HEADER};
    color: #A3B3AF;
    border-color: {BORDER};
}}
QPushButton#winBtn {{
    background: transparent;
    color: #E6EFEC;
    border: none;
    border-radius: 0;
    padding: 0;
    font-size: 14px;
    min-height: 0;
}}
QPushButton#winBtn:hover {{
    background: #1E3A38;
    color: #FFFFFF;
}}
QPushButton#winClose {{
    background: transparent;
    color: #E6EFEC;
    border: none;
    border-radius: 0;
    padding: 0;
    font-size: 14px;
    min-height: 0;
}}
QPushButton#winClose:hover {{
    background: #C0392B;
    color: #FFFFFF;
}}

/* ---------- Radio buttons ---------- */
QRadioButton {{
    spacing: 7px;
    color: {TEXT};
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 1px solid #B9C9C4;
    background: {CARD};
}}
QRadioButton::indicator:checked {{
    background: transparent;
    border: none;
    image: url("{_RADIO_ICON}");
}}
QRadioButton::indicator:unchecked:hover {{
    border-color: {PRIMARY};
}}

/* ---------- Checkboxes ---------- */
QCheckBox {{
    spacing: 7px;
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #B9C9C4;
    background: {CARD};
}}
QCheckBox::indicator:unchecked:hover {{
    border-color: {PRIMARY};
}}
QCheckBox::indicator:checked {{
    background: transparent;
    border: none;
    image: url("{_CHECK_ICON}");
}}

/* ---------- Tabs ---------- */
QTabWidget::pane {{
    border: none;
    background: transparent;
    top: 0;
}}
QTabWidget#mainTabs::pane {{
    border: none;
    background: transparent;
}}
QTabBar {{
    background: transparent;
}}
QTabWidget#mainTabs > QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 8px 8px;
    margin: 0;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 11px;
    font-weight: 500;
    min-width: 0;
}}
QTabWidget#mainTabs > QTabBar::tab:selected {{
    background: {TAB_ACTIVE};
    color: {PRIMARY};
    border-bottom: 2px solid {PRIMARY};
    font-weight: 600;
}}
QTabWidget#mainTabs > QTabBar::tab:hover:!selected {{
    color: {TEXT};
    background: #F7FAF9;
}}
QTabWidget#subTabs > QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 5px 10px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 11px;
    font-weight: 500;
}}
QTabWidget#subTabs > QTabBar::tab:selected {{
    color: {PRIMARY};
    border-bottom: 2px solid {PRIMARY};
    font-weight: 600;
}}
QTabWidget#subTabs > QTabBar::tab:hover:!selected {{
    color: {TEXT};
}}

/* ---------- Cards ---------- */
QGroupBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {TEXT};
    background: {CARD};
    font-size: 12px;
}}
QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QFrame#card QWidget {{
    background: transparent;
}}
QLabel#badgeInfo {{
    background: {INFO_BG};
    color: {INFO_TEXT};
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 8px;
    font-weight: 600;
}}
QLabel#badgeSuccess {{
    background: {SUCCESS_BG};
    color: {SUCCESS_TEXT};
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 8px;
    font-weight: 600;
}}
QLabel#badgeWarn {{
    background: {WARNING_BG};
    color: {WARNING_TEXT};
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 8px;
    font-weight: 600;
}}
QLabel#badgeError {{
    background: {ERROR_BG};
    color: {ERROR_TEXT};
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 8px;
    font-weight: 600;
}}

/* ---------- Log ---------- */
QTextEdit#logView {{
    background: {CARD};
    color: {TEXT};
    border: none;
    padding: 4px 6px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
}}
QTextEdit#logView span.info {{ color: {INFO_TEXT}; }}
QTextEdit#logView span.success {{ color: {SUCCESS_TEXT}; }}
QTextEdit#logView span.warning {{ color: {WARNING_TEXT}; }}
QTextEdit#logView span.error {{ color: {ERROR_TEXT}; }}

/* ---------- Tables ---------- */
QTableWidget, QTableView {{
    background: {CARD};
    alternate-background-color: #FBFCFB;
    color: {TEXT};
    gridline-color: {TABLE_HEADER};
    border: none;
    font-size: 10px;
}}
QHeaderView::section {{
    background: {TABLE_HEADER};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px;
    font-size: 9px;
    font-weight: 600;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background: {TAB_ACTIVE};
    color: {TEXT};
}}

/* ---------- Scrollbars ---------- */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #C9D6D2;
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A9BDB7;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #C9D6D2;
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #A9BDB7;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ---------- Splitter ---------- */
QSplitter::handle {{
    background: {BORDER};
}}
QSplitter::handle:hover {{
    background: #C9D6D2;
}}

/* ---------- Message boxes ---------- */
QMessageBox {{
    background: {BG};
}}
QMessageBox QLabel {{
    color: {TEXT};
}}

/* ---------- Menus ---------- */
QMenu {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {TAB_ACTIVE};
    color: {PRIMARY};
}}
"""
