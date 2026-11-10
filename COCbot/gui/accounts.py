# ==== COCbot/gui/accounts.py ====
"""Accounts / shared_prefs / auto-switch UI for MainWindow."""
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from COCbot.app import state as main
from COCbot.game.account.shared_prefs import SharedPrefsManager
from COCbot.game.account.switch_config import (
    ACCOUNTS_PER_PAGE,
    MAX_ACCOUNTS,
    save_switch_config,
)


class AccountsMixin:
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
        root.setContentsMargins(0, 10, 0, 10)
        root.setSpacing(10)

        profile_card = QFrame()
        profile_card.setObjectName("card")
        top = QVBoxLayout(profile_card)
        top.setContentsMargins(14, 12, 14, 12)
        top.setSpacing(8)
        profile_title = QLabel("Shared_prefs profile")
        profile_title.setStyleSheet(
            "font-size:13px; font-weight:600; color:#193431;")
        top.addWidget(profile_title)

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

        status = QHBoxLayout()
        self.acc_current_lbl = QLabel("Current: (chưa đặt)")
        self.acc_current_lbl.setStyleSheet("color:#13775F; font-weight:600;")
        status.addWidget(self.acc_current_lbl)
        status.addStretch()
        self.acc_root_lbl = QLabel("Root: kiểm tra khi dùng")
        self.acc_root_lbl.setStyleSheet("color:#657877; font-size:9px;")
        status.addWidget(self.acc_root_lbl)
        top.addLayout(status)
        root.addWidget(profile_card)

        grp = QGroupBox("Auto switch")
        g = QGridLayout(grp)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)

        self.switch_enable_chk = QCheckBox("Enable Switch Accounts")
        g.addWidget(self.switch_enable_chk, 0, 0, 1, 4)

        g.addWidget(QLabel("Accounts:"), 1, 0)
        self.switch_total_spin = QSpinBox()
        self.switch_total_spin.setRange(2, MAX_ACCOUNTS)
        g.addWidget(self.switch_total_spin, 1, 1)
        g.addWidget(QLabel("Attacks / acc:"), 1, 2)
        self.switch_max_spin = QSpinBox()
        self.switch_max_spin.setRange(1, 100)
        self.switch_max_spin.setToolTip(
            "Số trận mặc định cho mỗi account. Account nào có ô 'Trận' riêng "
            "(khác 0) sẽ dùng số đó.")
        g.addWidget(self.switch_max_spin, 1, 3)

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
        g.addLayout(trig_row, 2, 0, 1, 4)

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
        g.addLayout(full_row, 3, 0, 1, 4)

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

        self.acc_status_lbl = QLabel("Chưa có thao tác account.")
        self.acc_status_lbl.setWordWrap(True)
        self.acc_status_lbl.setStyleSheet("color:#657877; font-size:9px;")
        body.addWidget(self.acc_status_lbl)
        g.addLayout(body, 4, 0, 1, 4)
        root.addWidget(grp, 1)

        self.acc_mode_note = QLabel(
            "Shared_prefs: dùng adbd root sẵn có (MEmu/LDPlayer), "
            "không cần root thủ công."
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
        for row in self.switch_rows:
            row["cb"].toggled.connect(self._save_switch_ui)
            row["atk"].valueChanged.connect(self._save_switch_ui)
            row["combo"].currentTextChanged.connect(self._save_switch_ui)

        return w

    def _account_log(self, text):
        if hasattr(self, "acc_status_lbl"):
            self.acc_status_lbl.setText(
                f"{time.strftime('%H:%M:%S')} · {text}")

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
                root_text = mgr.root_label()
                short_root = (
                    "root: adbd OK" if "adbd root" in root_text else root_text)
                self.acc_root_lbl.setText(short_root)
                self.acc_root_lbl.setToolTip(root_text)
            else:
                self.acc_root_lbl.setText("Root: chưa chọn emulator")
                self.acc_root_lbl.setToolTip("")
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
        widgets = (self.switch_enable_chk,
                   self.switch_total_spin, self.switch_max_spin,
                   self.switch_by_attacks_chk, self.switch_by_time_chk,
                   self.switch_by_full_chk, self.switch_full_wait_spin,
                   self.switch_interval_spin)
        for w in widgets:
            w.blockSignals(True)
        self.switch_enable_chk.setChecked(bool(cfg.get("enabled")))
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

    def _save_switch_ui(self, *args):
        if getattr(self, "_loading_switch_ui", False):
            return
        cfg = self._switch_cfg
        cfg["enabled"] = self.switch_enable_chk.isChecked()
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
        for i, row in enumerate(self.switch_rows):
            cfg["accounts"][i] = {
                "enabled": row["cb"].isChecked(),
                "profile": row["combo"].currentText().strip(),
                "attacks": int(row["atk"].value()),
            }
        save_switch_config(cfg)
        self._update_switch_rows()

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
