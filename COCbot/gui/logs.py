# ==== COCbot/gui/logs.py ====
"""Bot log + attack log table logic for MainWindow."""
import os
import re
import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidgetItem,
    QWidget,
)
from PyQt5 import sip


LOG_LEVEL_STYLES = {
    "INFO": ("#EEF2F6", "#536D80"),
    "SUCCESS": ("#E8F4EC", "#13775F"),
    "WARNING": ("#FFF6E5", "#9A6B00"),
    "ERROR": ("#FFF3F1", "#A82921"),
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


class LogsMixin:
    def _append_log_row(self, level: str, text: str):
        if not hasattr(self, "log_table") or sip.isdeleted(self.log_table):
            return
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        if "•" in text:
            time_part, message = text.split("•", 1)
            time_str = time_part.strip()
            message = message.strip()
        else:
            time_str = time.strftime("%H:%M:%S")
            message = text
        # Avoid repeating the level token inside the EVENT column.
        for token in (level, f"[{level}]"):
            if message.upper().startswith(token.upper() + " "):
                message = message[len(token):].strip()
                break
        time_item = QTableWidgetItem(time_str)
        time_item.setForeground(QBrush(QColor("#657877")))
        time_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        bg, fg = LOG_LEVEL_STYLES.get(level, LOG_LEVEL_STYLES["INFO"])
        badge = QLabel(level)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:3px;"
            " padding:1px 5px; font-size:8px; font-weight:600;")
        badge_wrap = QWidget()
        badge_layout = QHBoxLayout(badge_wrap)
        badge_layout.setContentsMargins(4, 2, 4, 2)
        badge_layout.setSpacing(0)
        badge_layout.addWidget(badge, 0, Qt.AlignCenter)

        msg_item = QTableWidgetItem(message)
        msg_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        msg_item.setForeground(QBrush(QColor("#193431")))

        self.log_table.setItem(row, 0, time_item)
        self.log_table.setCellWidget(row, 1, badge_wrap)
        self.log_table.setItem(row, 2, msg_item)
        if self.auto_scroll_chk.isChecked():
            self.log_table.scrollToBottom()

    def _append_log(self, line: str):
        if sip.isdeleted(self):
            return
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
            self._append_log_row(level, text)

        if hasattr(self, "log_count_lbl"):
            self.log_count_lbl.setText(
                f"{len(self._log_lines)} events · All systems ready")

    def _on_log_filter_changed(self, value: str):
        self._log_filter = value or "All events"
        self.log_table.setRowCount(0)
        for level, text in self._log_lines:
            if self._log_filter == "All events" or self._log_filter == level:
                self._append_log_row(level, text)

    def _export_log(self):
        default = os.path.join(
            os.path.expanduser("~"), "mybot-log.txt")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export bot log", default, "Text files (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.writelines(f"[{level}] {text}\n" for level, text in self._log_lines)
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
