"""Theme tokens and a compact Qt style sheet for the new MVVM views."""

from __future__ import annotations

from PyQt5.QtWidgets import QApplication

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
SUCCESS_TEXT = "#13775F"
SUCCESS_BG = "#E8F4EC"
WARNING_TEXT = "#9A6B00"
WARNING_BG = "#FFF6E5"
ERROR_TEXT = "#A82921"
ERROR_BG = "#FFF3F1"

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
QMainWindow, QDialog {{ background: {BG}; }}
QLabel {{ background: transparent; }}
QLabel#muted {{ color: {TEXT_MUTED}; }}
QLabel#cardTitle {{ color: {TEXT}; font-size: 13px; font-weight: 600; }}
QLabel#cardSub {{ color: {TEXT_MUTED}; font-size: 10px; }}
QLabel#statusInfo {{ color: {TEXT_MUTED}; }}
QLabel#statusSuccess {{ color: {SUCCESS_TEXT}; }}
QLabel#statusWarning {{ color: {WARNING_TEXT}; }}
QLabel#statusError {{ color: {ERROR_TEXT}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 22px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {PRIMARY};
}}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
    color: #A3B3AF;
    background: {TABLE_HEADER};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {TAB_ACTIVE};
}}

QPushButton {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 12px;
    font-weight: 500;
    min-height: 28px;
}}
QPushButton:hover {{ border-color: {PRIMARY}; color: {PRIMARY}; }}
QPushButton:pressed {{ background: {TABLE_HEADER}; }}
QPushButton:disabled {{ color: #A3B3AF; border-color: {BORDER}; background: {TABLE_HEADER}; }}
QPushButton#primaryBtn {{
    background: {PRIMARY};
    color: #FFFFFF;
    border: 1px solid {PRIMARY};
    font-weight: 600;
}}
QPushButton#primaryBtn:hover {{ background: {PRIMARY_HOVER}; border-color: {PRIMARY_HOVER}; }}
QPushButton#primaryBtn:disabled {{ background: #9CC4BA; border-color: #9CC4BA; color: #F2F5F3; }}
QPushButton#stopBtn {{ background: {ERROR_BG}; color: {ERROR_TEXT}; border: 1px solid #D9A199; }}

QCheckBox {{ spacing: 7px; color: {TEXT}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid #B9C9C4; background: {CARD}; }}
QCheckBox::indicator:unchecked:hover {{ border-color: {PRIMARY}; }}
QCheckBox::indicator:checked {{ background: {PRIMARY}; border-color: {PRIMARY}; }}

QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 6px; }}
QFrame#card QWidget {{ background: transparent; }}
QGroupBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C9D6D2; border-radius: 4px; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QToolTip {{ background: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px 8px; border-radius: 4px; }}
QMessageBox {{ background: {BG}; }}
"""


def apply_theme(application: QApplication) -> None:
    """Apply the project style sheet to *application*."""
    application.setStyleSheet(GLOBAL_QSS)
