# ==== COCbot/gui/tabs/army_recipe.py ====
import os
import sys

import COCbot.app.paths
from COCbot.app.army_presets import (
    DEFAULT_SIDE,
    VALID_SIDES,
    get_preset,
    load_presets,
    normalize_recipe,
    save_presets,
)
from COCbot.app.troop_registry import (
    SIEGE,
    SPELLS,
    TROOPS,
    siege_icon_file,
    spell_icon_file,
    troop_icon_file,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

TEMPLATE_DIR = str(COCbot.app.paths.TEMPLATE_DIR)
ICON_DIR = os.path.join(TEMPLATE_DIR, "Smart_Auto_train", "Army Troops")
SPELL_ICON_DIR = os.path.join(TEMPLATE_DIR, "Smart_Auto_train", "Spells")
SIEGE_ICON_DIR = os.path.join(TEMPLATE_DIR, "Smart_Auto_train", "Siege Machines")

ARMY_SPACE_MAX = 260
SPELL_SPACE_MAX = 11


class TroopCell(QWidget):
    """1 ô quân: icon + tên + spinner số lượng (Gọn, không nút mũi tên)."""
    changed = pyqtSignal()

    def __init__(self, name, housing, icon_dir, max_count=200, icon_file=None):
        super().__init__()
        self.name = name
        self.housing = housing

        self.setFixedSize(64, 86)
        self.setStyleSheet("""
            TroopCell {
                background: rgba(17, 29, 49, 200);
                border: 1px solid #243854;
                border-radius: 7px;
            }
            TroopCell:hover {
                background: rgba(22, 36, 59, 230);
                border: 1px solid #e8b64c;
            }
        """)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(2, 4, 2, 4)
        vbox.setSpacing(1)

        # 1. Icon — dùng đúng tên file icon của registry
        icon_lbl = QLabel()
        icon_path = os.path.join(icon_dir, (icon_file or name) + ".png")
        if os.path.isfile(icon_path):
            pix = QPixmap(icon_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("?")
            icon_lbl.setStyleSheet("color:#888; font-size:20px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        vbox.addWidget(icon_lbl)

        # 2. Tên
        name_lbl = QLabel(name.replace("_", " ").title())
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("color:#dbe7f7; font-size:8px; font-weight:bold;")
        name_lbl.setMinimumWidth(1)
        vbox.addWidget(name_lbl)

        # 3. Spinner
        self.spin = QSpinBox()
        self.spin.setRange(0, max_count)
        self.spin.setValue(0)
        self.spin.setFixedHeight(20)
        self.spin.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spin.setAlignment(Qt.AlignCenter)

        self.spin.setStyleSheet("""
            QSpinBox {
                background: #0b1424;
                border: 1px solid #243854;
                border-radius: 4px;
                color: #ffd76a;
                padding: 0px;
                margin: 0px;
            }
            QSpinBox:focus {
                background: #111d31;
                border: 1px solid #e8b64c;
            }
        """)
        self.spin.valueChanged.connect(self.changed.emit)
        vbox.addWidget(self.spin)

    def get_count(self):
        return self.spin.value()

    def set_count(self, n):
        self.spin.blockSignals(True)
        self.spin.setValue(int(n))
        self.spin.blockSignals(False)

    def clear(self):
        self.set_count(0)


class RecipeGrid(QWidget):
    """Grid các ô quân cho 1 loại."""
    changed = pyqtSignal()

    def __init__(self, items, icon_dir, max_count=200, columns=6, icon_file_getter=None):
        super().__init__()
        self.cells = {}
        self.housing = {}
        self.icon_file_getter = icon_file_getter

        grid = QGridLayout(self)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(6)

        for idx, (name, (housing, _cat)) in enumerate(items.items()):
            row, col = divmod(idx, columns)
            icon_file = icon_file_getter(name) if icon_file_getter else name
            cell = TroopCell(name, housing, icon_dir, max_count, icon_file=icon_file)
            cell.changed.connect(self.changed.emit)
            self.cells[name] = cell
            self.housing[name] = housing
            grid.addWidget(cell, row, col)

        grid.setColumnStretch(columns, 1)
        grid.setRowStretch(grid.rowCount(), 1)
        grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

    def get_selected(self):
        return {n: c.get_count() for n, c in self.cells.items() if c.get_count() > 0}

    def set_selected(self, data):
        """Đặt lại TOÀN BỘ grid theo data (ô không có trong data -> 0)."""
        data = data or {}
        for name, cell in self.cells.items():
            cell.set_count(data.get(name, 0))

    def total_space(self):
        return sum(self.housing[n] * c.get_count() for n, c in self.cells.items())

    def clear(self):
        for cell in self.cells.values():
            cell.clear()


class ArmyRecipeTab(QWidget):
    """Tab Army: preset + grid + space calc."""
    recipe_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_presets_to_combo()
        self._on_preset_selected(self.preset_combo.currentText())

    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(6)

        # ── Thanh Công Cụ (Preset & Hướng) ──
        preset_bar = QHBoxLayout()

        lbl = QLabel("Preset:")
        lbl.setStyleSheet("color:#e8b64c; font-weight:bold;")
        preset_bar.addWidget(lbl)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(150)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        preset_bar.addWidget(self.preset_combo)

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._on_new_preset)
        preset_bar.addWidget(self.new_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._on_save_preset)
        preset_bar.addWidget(self.save_btn)

        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self._on_delete_preset)
        preset_bar.addWidget(self.del_btn)

        preset_bar.addSpacing(20)

        # --- CHỌN HƯỚNG THẢ QUÂN (lưu theo preset) ---
        lbl_side = QLabel("Hướng thả:")
        lbl_side.setStyleSheet("color:#e8b64c; font-weight:bold;")
        preset_bar.addWidget(lbl_side)

        self.side_combo = QComboBox()
        self.side_combo.addItems(VALID_SIDES)
        self.side_combo.setStyleSheet(
            "background: #111d31; color: #dbe7f7; padding: 3px;"
            " border: 1px solid #243854; border-radius: 4px;"
        )
        self.side_combo.currentTextChanged.connect(self._on_side_changed)
        preset_bar.addWidget(self.side_combo)

        preset_bar.addSpacing(20)
        self.check_troops_chk = QCheckBox("Check quân")
        self.check_troops_chk.setChecked(False)
        self.check_troops_chk.setStyleSheet("color:#e8b64c; font-weight:bold;")
        self.check_troops_chk.setToolTip(
            "Bật: kiểm tra/train quân trước khi tìm trận.\n"
            "Tắt (mặc định): bỏ qua kiểm tra, cứ tìm trận đủ điều kiện rồi đánh."
        )
        preset_bar.addWidget(self.check_troops_chk)

        preset_bar.addStretch()
        vbox.addLayout(preset_bar)

        # ── Sub-tabs: 4 Tabs (Elixir, Dark, Spells, Siege) ──
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #243854; background: rgba(13,23,39,200); border-radius: 6px; }
            QTabBar::tab { background:#111d31; color:#8fa3bf; padding:5px 12px; border:1px solid #243854; border-bottom:none; }
            QTabBar::tab:selected { background:#e8b64c; color:#080d18; border-color:#ffd76a; font-weight:700; }
        """)

        elixir_troops = {k: v for k, v in TROOPS.items() if v[1] == "elixir"}
        dark_troops = {k: v for k, v in TROOPS.items() if v[1] == "dark"}

        # Tab 1: Elixir Troops
        elixir_widget = QWidget()
        elixir_v = QVBoxLayout(elixir_widget)
        elixir_v.setContentsMargins(0, 0, 0, 0)
        self.troop_grid_elixir = RecipeGrid(
            elixir_troops, ICON_DIR, icon_file_getter=troop_icon_file)
        self.troop_grid_elixir.changed.connect(self._on_grid_changed)
        elixir_v.addWidget(self.troop_grid_elixir)
        self.sub_tabs.addTab(elixir_widget, "Elixir Troops")

        # Tab 2: Dark Troops
        dark_widget = QWidget()
        dark_v = QVBoxLayout(dark_widget)
        dark_v.setContentsMargins(0, 0, 0, 0)
        self.troop_grid_dark = RecipeGrid(
            dark_troops, ICON_DIR, icon_file_getter=troop_icon_file)
        self.troop_grid_dark.changed.connect(self._on_grid_changed)
        dark_v.addWidget(self.troop_grid_dark)
        self.sub_tabs.addTab(dark_widget, "Dark Troops")

        # Tab 3: Spells
        spells_widget = QWidget()
        spells_v = QVBoxLayout(spells_widget)
        spells_v.setContentsMargins(0, 0, 0, 0)
        self.spell_grid = RecipeGrid(
            SPELLS, SPELL_ICON_DIR, max_count=20, icon_file_getter=spell_icon_file)
        self.spell_grid.changed.connect(self._on_grid_changed)
        spells_v.addWidget(self.spell_grid)
        self.sub_tabs.addTab(spells_widget, "Spells")

        # Tab 4: Siege
        siege_widget = QWidget()
        siege_v = QVBoxLayout(siege_widget)
        siege_v.setContentsMargins(0, 0, 0, 0)
        self.siege_grid = RecipeGrid(
            SIEGE, SIEGE_ICON_DIR, max_count=10, icon_file_getter=siege_icon_file)
        self.siege_grid.changed.connect(self._on_grid_changed)
        siege_v.addWidget(self.siege_grid)
        self.sub_tabs.addTab(siege_widget, "Siege")

        vbox.addWidget(self.sub_tabs, 1)

        # ── Footer: space calculator ──
        footer = QFrame()
        footer.setStyleSheet(
            "QFrame { background: rgba(8,13,24,220); border-top: 1px solid #243854; }"
        )
        footer_h = QHBoxLayout(footer)

        self.space_lbl = QLabel("Army Space: 0 / 260   |   Spell Space: 0 / 11")
        self.space_lbl.setStyleSheet(
            "color:#e8b64c; font-weight:bold; padding:6px;"
        )
        footer_h.addWidget(self.space_lbl)
        footer_h.addStretch()

        vbox.addWidget(footer)

    # ────────────────────────────────────────────────────────
    # Preset logic
    # ────────────────────────────────────────────────────────
    def _load_presets_to_combo(self):
        data = load_presets()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(list(data["presets"].keys()))
        active = data.get("active", "")
        idx = self.preset_combo.findText(active)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)

    def _on_preset_selected(self, name):
        """Nạp preset vào grid + khôi phục hướng thả đã lưu."""
        if not name:
            return
        recipe = get_preset(name)
        if not recipe:
            return
        recipe = normalize_recipe(recipe)
        self._apply_recipe_to_ui(recipe)

    def _apply_recipe_to_ui(self, recipe):
        troops = recipe.get("troops", {})
        self.troop_grid_elixir.set_selected(troops)
        self.troop_grid_dark.set_selected(troops)

        self.spell_grid.set_selected(recipe.get("spells", {}))
        self.siege_grid.set_selected(recipe.get("siege", {}))

        side = recipe.get("side") or DEFAULT_SIDE
        idx = self.side_combo.findText(side)
        self.side_combo.blockSignals(True)
        self.side_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.side_combo.blockSignals(False)

        self._update_space_label()

    def _collect_current(self):
        troops = {}
        troops.update(self.troop_grid_elixir.get_selected())
        troops.update(self.troop_grid_dark.get_selected())
        return normalize_recipe({
            "troops": troops,
            "spells": self.spell_grid.get_selected(),
            "siege":  self.siege_grid.get_selected(),
            "side":   self.side_combo.currentText(),
        })

    def _on_save_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Save", "Chưa có tên preset.")
            return
        data = load_presets()
        data["presets"][name] = self._collect_current()
        data["active"] = name
        if save_presets(data):
            QMessageBox.information(self, "Save", f"Đã lưu preset '{name}'.")
            self.recipe_changed.emit()

    def _on_new_preset(self):
        name, ok = QInputDialog.getText(self, "New Preset", "Tên preset mới:")
        if not ok or not name.strip():
            return
        name = name.strip()
        data = load_presets()
        if name in data["presets"]:
            QMessageBox.warning(self, "New", f"'{name}' đã tồn tại.")
            return
        data["presets"][name] = normalize_recipe({})
        data["active"] = name
        if not save_presets(data):
            QMessageBox.warning(self, "New", "Không lưu được preset.")
            return

        self._load_presets_to_combo()
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText(name)
        self.preset_combo.blockSignals(False)

        self._clear_grids()
        self.recipe_changed.emit()

    def _on_delete_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Delete", f"Xoá preset '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        data = load_presets()
        data["presets"].pop(name, None)
        if data.get("active") == name:
            data["active"] = next(iter(data["presets"]), "")
        save_presets(data)
        self._load_presets_to_combo()

        remaining = self.preset_combo.currentText()
        if remaining:
            self._on_preset_selected(remaining)
        else:
            self._clear_grids()
        self.recipe_changed.emit()

    # ────────────────────────────────────────────────────────
    # Signal / helpers
    # ────────────────────────────────────────────────────────
    def _clear_grids(self):
        self.troop_grid_elixir.clear()
        self.troop_grid_dark.clear()
        self.spell_grid.clear()
        self.siege_grid.clear()
        self.side_combo.setCurrentIndex(0)
        self._update_space_label()

    def _on_side_changed(self, _text):
        self.recipe_changed.emit()

    def _on_grid_changed(self):
        self._update_space_label()
        self.recipe_changed.emit()

    def _update_space_label(self):
        troop_space = (self.troop_grid_elixir.total_space() +
                       self.troop_grid_dark.total_space())
        spell_space = self.spell_grid.total_space()

        t_color = "#FF4444" if troop_space > ARMY_SPACE_MAX else "#FFF"
        s_color = "#FF4444" if spell_space > SPELL_SPACE_MAX else "#FFF"

        self.space_lbl.setText(
            f"Army Space: <span style='color:{t_color}'>{troop_space}</span> / {ARMY_SPACE_MAX}"
            f"   |   Spell Space: <span style='color:{s_color}'>{spell_space}</span> / {SPELL_SPACE_MAX}"
        )

    # ────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────
    def get_current_recipe(self):
        return self._collect_current()

    def get_active_preset_name(self):
        return self.preset_combo.currentText().strip()

    def get_active_recipe(self):
        return self._collect_current()

    def get_active_name(self):
        return self.preset_combo.currentText()

    def get_attack_side(self):
        return self.side_combo.currentText()

    def get_check_troops(self):
        return self.check_troops_chk.isChecked()
