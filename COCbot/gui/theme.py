"""Clash-of-Clans-inspired visual theme for the GUI.

Kept in one place so every tab/dialog shares the same palette. The palette is
deep navy + gold, matching the Clash of Clans logo used in the header.
"""

from __future__ import annotations

# Palette
BG_DEEP = "#080d18"
BG_NAVY = "#0d1727"
BG_PANEL = "#111d31"
BG_PANEL_2 = "#16243b"
BORDER = "#243854"
BORDER_SOFT = "#1c2b42"
GOLD = "#e8b64c"
GOLD_BRIGHT = "#ffd76a"
GOLD_DARK = "#9c741f"
BLUE = "#4c8dff"
CYAN = "#4fd1c5"
TEXT = "#e8eef8"
TEXT_MUTED = "#8fa3bf"
DANGER = "#e05353"
SUCCESS = "#5fd38d"

GLOBAL_QSS = f"""
* {{
    font-family: "Segoe UI", "Arial", sans-serif;
    outline: none;
}}
QWidget {{
    color: {TEXT};
    selection-background-color: {GOLD_DARK};
    selection-color: {BG_DEEP};
}}
QMainWindow, QDialog {{
    background: {BG_DEEP};
}}
QLabel {{
    background: transparent;
}}
QToolTip {{
    background: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {GOLD};
    padding: 6px 8px;
    border-radius: 4px;
}}

/* ---------- Inputs ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 3px 6px;
    min-height: 20px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {GOLD};
    background: {BG_PANEL_2};
}}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
    color: {TEXT_MUTED};
    background: {BG_DEEP};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {GOLD_DARK};
    selection-color: {BG_DEEP};
}}

/* ---------- Buttons ---------- */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {BG_PANEL_2}, stop:1 {BG_PANEL});
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    font-weight: 600;
}}
QPushButton:hover {{
    border-color: {GOLD};
    color: {GOLD_BRIGHT};
}}
QPushButton:pressed {{
    background: {BG_DEEP};
    padding-top: 6px;
}}
QPushButton:disabled {{
    color: #5a6a80;
    border-color: {BORDER_SOFT};
    background: {BG_DEEP};
}}
QPushButton#startBtn, QPushButton#endBtn {{
    background: transparent;
    border: none;
    padding: 0;
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
    border: 1px solid {BORDER};
    background: {BG_PANEL};
}}
QRadioButton::indicator:checked {{
    background: {GOLD};
    border: 1px solid {GOLD_BRIGHT};
}}
QRadioButton::indicator:unchecked:hover {{
    border-color: {GOLD};
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
    border: 1px solid {BORDER};
    background: {BG_PANEL};
    image: none;
}}
QCheckBox::indicator:unchecked {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    image: none;
}}
QCheckBox::indicator:unchecked:hover {{
    border-color: {GOLD};
}}
QCheckBox::indicator:checked {{
    background: {GOLD};
    border: 1px solid {GOLD_BRIGHT};
    image: none;
}}

/* ---------- Tabs ---------- */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: rgba(13, 23, 39, 238);
    border-radius: 0 0 8px 8px;
    top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: {BG_PANEL};
    color: {TEXT_MUTED};
    padding: 6px 12px;
    margin-right: 3px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    font-size: 10px;
    font-weight: 700;
    min-width: 60px;
}}
QTabBar::tab:selected {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {GOLD}, stop:1 {GOLD_DARK});
    color: {BG_DEEP};
    border-color: {GOLD_BRIGHT};
}}
QTabBar::tab:hover:!selected {{
    background: {BG_PANEL_2};
    color: {TEXT};
    border-color: {GOLD_DARK};
}}

/* ---------- Group boxes / frames ---------- */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 10px;
    padding: 8px 8px 6px 8px;
    background: rgba(17, 29, 49, 210);
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {GOLD};
}}
QFrame#card {{
    background: rgba(17, 29, 49, 220);
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

/* ---------- Tables ---------- */
QTableWidget, QTableView {{
    background: {BG_PANEL};
    alternate-background-color: {BG_PANEL_2};
    color: {TEXT};
    gridline-color: {BORDER_SOFT};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QHeaderView::section {{
    background: {BG_PANEL_2};
    color: {GOLD};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px;
    font-weight: 700;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background: {GOLD_DARK};
    color: {BG_DEEP};
}}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {GOLD_DARK};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {GOLD_DARK};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ---------- Splitter ---------- */
QSplitter::handle {{
    background: {BORDER_SOFT};
}}
QSplitter::handle:hover {{
    background: {GOLD_DARK};
}}

/* ---------- Message boxes ---------- */
QMessageBox {{
    background: {BG_NAVY};
}}
QMessageBox QLabel {{
    color: {TEXT};
}}
"""
