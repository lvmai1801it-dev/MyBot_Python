# ==== COCbot/gui/tabs/village_tabs.py ====
"""Village (General / Upgrade) tab widget builder."""
import os

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from COCbot.gui.constants import TEMPLATES_DIR

hdrF = QFont("Segoe UI", 12, QFont.Bold)
labF = QFont("Segoe UI", 10, QFont.Bold)


def build_village_tabs(win):
    # ===== TAB 1: General tab =====
    gen_tab = QWidget()
    gen_root = QVBoxLayout(gen_tab)
    gen_root.setContentsMargins(0, 8, 0, 8)
    gen_root.setSpacing(8)

    def _card(title, subtitle=""):
        card = QFrame()
        card.setObjectName("card")
        box = QVBoxLayout(card)
        box.setContentsMargins(12, 10, 12, 10)
        box.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet("font-size:12px; font-weight:600; color:#193431;")
        box.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setStyleSheet("font-size:9px; color:#657877;")
            s.setWordWrap(True)
            box.addWidget(s)
        return card, box

    def _form_grid():
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(2, 1)
        return grid

    def _add_field(grid, row, icon_file, text, widget, width=130):
        label_box = QHBoxLayout()
        label_box.setSpacing(6)
        icon = QLabel()
        path = os.path.join(TEMPLATES_DIR, icon_file)
        if os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                icon.setPixmap(
                    pix.scaledToHeight(16, Qt.SmoothTransformation))
        label_box.addWidget(icon)
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size:11px; color:#193431;")
        label_box.addWidget(lbl)
        label_box.addStretch()
        grid.addLayout(label_box, row, 0)
        widget.setFixedWidth(width)
        widget.setFixedHeight(26)
        grid.addWidget(widget, row, 1)

    # Card 1: Loot filter
    loot_card, loot_box = _card(
        "Loot filter", "Bỏ qua base có loot thấp hơn ngưỡng.")
    loot_grid = _form_grid()
    win.gold_entry = QLineEdit(str(win.settings.get("gold_threshold", 65000)))
    win.elixir_entry = QLineEdit(
        str(win.settings.get("elixir_threshold", 65000)))
    win.dark_entry = QLineEdit(
        str(win.settings.get("dark_elixir_threshold", 5)))
    for e in (win.gold_entry, win.elixir_entry, win.dark_entry):
        e.setFont(labF)
    _add_field(loot_grid, 0, "icon_gold.png", "Gold", win.gold_entry)
    _add_field(loot_grid, 1, "icon_elixir.png", "Elixir", win.elixir_entry)
    _add_field(loot_grid, 2, "icon_de.png", "Dark Elixir", win.dark_entry)
    loot_box.addLayout(loot_grid)
    gen_root.addWidget(loot_card)

    # Card 2: Clan
    clan_card, clan_box = _card(
        "Clan", "Xin quân từ Clan Castle qua Clan Chat.")
    win.req_chk = QCheckBox("Enable Request Troops")
    win.req_chk.setFont(hdrF)
    win.req_chk.setChecked(win.settings.get("request_troops", False))
    clan_box.addWidget(win.req_chk)
    req_note = QLabel(
        "Bot mở Clan Chat và gửi yêu cầu quân khi bắt đầu chu kỳ.")
    req_note.setWordWrap(True)
    req_note.setStyleSheet("font-size:10px; color:#657877;")
    clan_box.addWidget(req_note)
    gen_root.addWidget(clan_card)
    gen_root.addStretch()

    # ===== TAB 1.5: Upgrade tab =====
    upgrade_tab = QWidget()
    up_page = QVBoxLayout(upgrade_tab)
    up_page.setContentsMargins(0, 0, 0, 0)
    up_page.setSpacing(0)

    up_tabs = QTabWidget()
    up_tabs.setObjectName("subTabs")
    up_tabs.setDocumentMode(True)
    win.upgrade_tabs = up_tabs

    # --- Wall upgrade ---
    wall_page = QWidget()
    wall_root = QVBoxLayout(wall_page)
    wall_root.setContentsMargins(0, 8, 0, 8)
    wall_root.setSpacing(8)
    wall_card, wall_box = _card(
        "Wall upgrade", "Tự động nâng tường khi đủ tài nguyên.")
    win.upgrade_chk = QCheckBox("Enable Upgrade Wall")
    win.upgrade_chk.setFont(hdrF)
    win.upgrade_chk.setChecked(win.settings.get("upgrade_wall", False))
    wall_box.addWidget(win.upgrade_chk)

    wall_grid = _form_grid()
    win.wall_gold_entry = QLineEdit(
        str(win.settings.get("wall_gold_threshold", 5000000)))
    win.wall_elixir_entry = QLineEdit(
        str(win.settings.get("wall_elixir_threshold", 5000000)))
    win.wall_level_spin = QSpinBox()
    win.wall_level_spin.setRange(8, 18)
    win.wall_level_spin.setValue(win.settings.get("wall_level", 8))
    for w in (win.wall_gold_entry, win.wall_elixir_entry,
              win.wall_level_spin):
        w.setFont(labF)
    _add_field(wall_grid, 0, "icon_gold.png", "Gold threshold",
               win.wall_gold_entry)
    _add_field(wall_grid, 1, "icon_elixir.png", "Elixir threshold",
               win.wall_elixir_entry)
    _add_field(wall_grid, 2, "icon_wall.png", "Target wall level",
               win.wall_level_spin)
    wall_box.addLayout(wall_grid)
    wall_root.addWidget(wall_card)

    wall_tips = QFrame()
    wall_tips.setObjectName("card")
    wtips = QVBoxLayout(wall_tips)
    wtips.setContentsMargins(12, 10, 12, 10)
    wtips.setSpacing(6)
    wt_title = QLabel("Cách hoạt động")
    wt_title.setStyleSheet("font-size:12px; font-weight:600; color:#193431;")
    wtips.addWidget(wt_title)
    for line in (
        "Kiểm tra kho vàng/tiêu mỗi chu kỳ.",
        "Chỉ nâng khi đạt ngưỡng đã đặt.",
        "Level mục tiêu từ 8 đến 18.",
    ):
        bullet = QLabel(f"•  {line}")
        bullet.setWordWrap(True)
        bullet.setStyleSheet("font-size:10px; color:#657877;")
        wtips.addWidget(bullet)
    wall_root.addWidget(wall_tips)
    wall_root.addStretch()
    up_tabs.addTab(wall_page, "Wall upgrade")

    # --- Hero upgrade ---
    hero_page = QWidget()
    hero_root = QVBoxLayout(hero_page)
    hero_root.setContentsMargins(0, 8, 0, 8)
    hero_root.setSpacing(8)
    hero_card, hero_box = _card(
        "Hero upgrade", "Tick các tướng muốn ưu tiên nâng cấp.")
    win.upgrade_hero_chk = QCheckBox("Enable Hero Upgrade")
    win.upgrade_hero_chk.setChecked(
        win.settings.get("upgrade_hero", False))
    hero_box.addWidget(win.upgrade_hero_chk)

    hero_names = (
        ("Barbarian King", "barbarian_king.png"),
        ("Archer Queen", "archer_queen.png"),
        ("Minion Prince", "minion_prince.png"),
        ("Grand Warden", "grand_warden.png"),
        ("Royal Champion", "royal_champion.png"),
        ("Dragon Duke", "dragon_duke.png"),
    )
    saved_hero = set(win.settings.get("hero_priorities", []) or [])
    hero_icon_dir = os.path.join(TEMPLATES_DIR, "upgrade", "hero")
    hero_grid = QGridLayout()
    hero_grid.setHorizontalSpacing(10)
    hero_grid.setVerticalSpacing(6)
    win.hero_checks = {}
    for i, (name, icon_file) in enumerate(hero_names):
        cb = QCheckBox(name)
        cb.setChecked(name in saved_hero)
        icon_path = os.path.join(hero_icon_dir, icon_file)
        if os.path.exists(icon_path):
            cb.setIcon(QIcon(icon_path))
            cb.setIconSize(QSize(28, 28))
        cb.setMinimumHeight(32)
        hero_grid.addWidget(cb, i // 2, i % 2)
        win.hero_checks[name] = cb
    hero_box.addLayout(hero_grid)

    hero_note = QLabel(
        "Chưa hỗ trợ tự động. Cấu hình được lưu để dùng khi logic "
        "nâng Hero được thêm.")
    hero_note.setWordWrap(True)
    hero_note.setStyleSheet("font-size:10px; color:#9A6B00;")
    hero_box.addWidget(hero_note)
    hero_root.addWidget(hero_card)
    hero_root.addStretch()
    up_tabs.addTab(hero_page, "Hero upgrade")

    # --- Defense upgrade ---
    defense_page = QWidget()
    defense_root = QVBoxLayout(defense_page)
    defense_root.setContentsMargins(0, 8, 0, 8)
    defense_root.setSpacing(8)
    defense_card, defense_box = _card(
        "Defense upgrade", "Ưu tiên nâng công trình phòng thủ.")
    win.upgrade_defense_chk = QCheckBox("Enable Defense Upgrade")
    win.upgrade_defense_chk.setChecked(
        win.settings.get("upgrade_defense", False))
    defense_box.addWidget(win.upgrade_defense_chk)

    defense_names = (
        "Air Sweeper", "Air Defense", "Eagle Artillery", "Archer Tower",
        "Bomb Tower", "X-Bow", "Cannon", "Inferno Tower", "Firespitter",
        "Multi-Archer Tower", "Ricochet Cannon", "Monolith", "Mortar",
        "Scattershot", "Spell Tower", "Hidden Tesla", "Wizard Tower",
    )
    saved_defense = set(win.settings.get("defense_priorities", []) or [])
    defense_grid = QGridLayout()
    defense_grid.setHorizontalSpacing(10)
    defense_grid.setVerticalSpacing(4)
    win.defense_checks = {}
    for i, name in enumerate(defense_names):
        cb = QCheckBox(name)
        cb.setChecked(name in saved_defense)
        defense_grid.addWidget(cb, i // 2, i % 2)
        win.defense_checks[name] = cb
    defense_box.addLayout(defense_grid)

    defense_note = QLabel(
        "Chưa hỗ trợ tự động. Tick các công trình muốn ưu tiên; "
        "cấu hình được lưu lại.")
    defense_note.setWordWrap(True)
    defense_note.setStyleSheet("font-size:10px; color:#9A6B00;")
    defense_box.addWidget(defense_note)
    defense_root.addWidget(defense_card)
    defense_root.addStretch()
    up_tabs.addTab(defense_page, "Defense")

    # --- Army buildings ---
    army_page = QWidget()
    army_root = QVBoxLayout(army_page)
    army_root.setContentsMargins(0, 8, 0, 8)
    army_root.setSpacing(8)
    army_card, army_box = _card(
        "Army buildings", "Ưu tiên nâng công trình quân đội.")
    win.upgrade_army_chk = QCheckBox("Enable Army Building Upgrade")
    win.upgrade_army_chk.setChecked(
        win.settings.get("upgrade_army", False))
    army_box.addWidget(win.upgrade_army_chk)

    army_names = (
        "Clan Castle", "Barracks", "Dark Barracks", "Hero Hall",
        "Laboratory", "Dark Spell Factory", "Pet House", "Workshop",
        "Blacksmith", "Spell Factory", "Army Camp",
    )
    saved_army = set(win.settings.get("army_priorities", []) or [])
    army_grid = QGridLayout()
    army_grid.setHorizontalSpacing(10)
    army_grid.setVerticalSpacing(4)
    win.army_checks = {}
    for i, name in enumerate(army_names):
        cb = QCheckBox(name)
        cb.setChecked(name in saved_army)
        army_grid.addWidget(cb, i // 2, i % 2)
        win.army_checks[name] = cb
    army_box.addLayout(army_grid)

    army_note = QLabel(
        "Chưa hỗ trợ tự động. Tick các công trình muốn ưu tiên; "
        "cấu hình được lưu lại.")
    army_note.setWordWrap(True)
    army_note.setStyleSheet("font-size:10px; color:#9A6B00;")
    army_box.addWidget(army_note)
    army_root.addWidget(army_card)
    army_root.addStretch()
    up_tabs.addTab(army_page, "Army")

    # --- Resource upgrade ---
    resource_page = QWidget()
    resource_root = QVBoxLayout(resource_page)
    resource_root.setContentsMargins(0, 8, 0, 8)
    resource_root.setSpacing(8)
    resource_card, resource_box = _card(
        "Resource upgrade", "Ưu tiên nâng mỏ / collector / kho.")
    win.upgrade_resource_chk = QCheckBox("Enable Resource Upgrade")
    win.upgrade_resource_chk.setChecked(
        win.settings.get("upgrade_resource", False))
    resource_box.addWidget(win.upgrade_resource_chk)

    resource_names = (
        "Dark Elixir Drill", "Dark Elixir Storage", "Elixir Collector",
        "Elixir Storage", "Gold Mine", "Gold Storage", "Helper Hut",
    )
    saved_resource = set(win.settings.get("resource_priorities", []) or [])
    resource_grid = QGridLayout()
    resource_grid.setHorizontalSpacing(10)
    resource_grid.setVerticalSpacing(4)
    win.resource_checks = {}
    for i, name in enumerate(resource_names):
        cb = QCheckBox(name)
        cb.setChecked(name in saved_resource)
        resource_grid.addWidget(cb, i // 2, i % 2)
        win.resource_checks[name] = cb
    resource_box.addLayout(resource_grid)

    resource_note = QLabel(
        "Chưa hỗ trợ tự động. Tick các công trình muốn ưu tiên; "
        "cấu hình được lưu lại.")
    resource_note.setWordWrap(True)
    resource_note.setStyleSheet("font-size:10px; color:#9A6B00;")
    resource_box.addWidget(resource_note)
    resource_root.addWidget(resource_card)
    resource_root.addStretch()
    up_tabs.addTab(resource_page, "Resource")

    # --- Other upgrades ---
    other_page = QWidget()
    other_root = QVBoxLayout(other_page)
    other_root.setContentsMargins(0, 8, 0, 8)
    other_root.setSpacing(8)
    other_card, other_box = _card(
        "Other upgrade", "Nâng cấp công trình bất kỳ (tên tự nhập).")
    win.upgrade_other_chk = QCheckBox("Enable Other Upgrade")
    win.upgrade_other_chk.setChecked(
        win.settings.get("upgrade_other", False))
    other_box.addWidget(win.upgrade_other_chk)

    win.other_buildings_entry = QLineEdit()
    win.other_buildings_entry.setPlaceholderText(
        "Town Hall, Builder's Hut, ...")
    saved_other = win.settings.get("other_buildings", []) or []
    if isinstance(saved_other, (list, tuple)):
        win.other_buildings_entry.setText(", ".join(saved_other))
    else:
        win.other_buildings_entry.setText(str(saved_other))
    other_box.addWidget(win.other_buildings_entry)

    other_note = QLabel(
        "Nhập tên công trình, phân tách bằng dấu phẩy. "
        "Chưa hỗ trợ tự động; cấu hình được lưu lại.")
    other_note.setWordWrap(True)
    other_note.setStyleSheet("font-size:10px; color:#9A6B00;")
    other_box.addWidget(other_note)
    other_root.addWidget(other_card)
    other_root.addStretch()
    up_tabs.addTab(other_page, "Other")

    up_page.addWidget(up_tabs)

    wall_widgets = [
        win.wall_gold_entry,
        win.wall_elixir_entry,
        win.wall_level_spin,
    ]

    def apply_state(enabled: bool, widgets):
        for w in widgets:
            w.setEnabled(enabled)
            w.setWindowOpacity(1.0 if enabled else 0.55)

    apply_state(win.upgrade_chk.isChecked(), wall_widgets)
    win.upgrade_chk.toggled.connect(
        lambda on: apply_state(on, wall_widgets))
    return gen_tab, upgrade_tab
