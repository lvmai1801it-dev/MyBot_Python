# troop_registry.py
"""Danh sách quân / spell / siege dùng chung cho GUI, preset và bot đánh.

Quy ước key (QUAN TRỌNG):
    key = tên file icon (snake_case) trong
        Templates/Smart_Auto_train/Army Troops/    -> troop
        Templates/Smart_Auto_train/Spells/         -> spell
        Templates/Smart_Auto_train/Siege Machines/ -> siege

    army_presets.json, army_recipe_tab.py và attacks/attacks.py đều dùng
    chung key này, nên không còn chuyện "hogrider" vs "hog_rider" hay
    "healing" vs "heal.png" làm bot không tìm thấy tab/quân.

    Các tên cũ vẫn được alias về key chuẩn để preset JSON cũ đọc được.
"""


def _norm(name):
    """Chuẩn hoá 1 tên bất kỳ về dạng snake_case thường."""
    return str(name or "").strip().lower().replace(" ", "_").replace("-", "_")


# ═══════════════════════════════════════════════════════════════
# TROOPS — key = tên file icon, value = (housing space, category)
# ═══════════════════════════════════════════════════════════════
TROOPS = {
    # ── Elixir troops ──
    "barbarian":       (1,  "elixir"),
    "archer":          (1,  "elixir"),
    "goblin":          (1,  "elixir"),
    "giant":           (5,  "elixir"),
    "wall_breaker":    (2,  "elixir"),
    "balloon":         (5,  "elixir"),
    "wizard":          (4,  "elixir"),
    "healer":          (14, "elixir"),
    "dragon":          (20, "elixir"),
    "pekka":           (25, "elixir"),
    "baby_dragon":     (10, "elixir"),
    "miner":           (6,  "elixir"),
    "electro_dragon":  (30, "elixir"),
    "yeti":            (25, "elixir"),
    "dragon_rider":    (25, "elixir"),
    "electro_titan":   (32, "elixir"),
    "root_rider":      (20, "elixir"),
    "thrower":         (12, "elixir"),

    # ── Dark Elixir troops ──
    "minion":          (2,  "dark"),
    "hog_rider":       (5,  "dark"),
    "valkyrie":        (8,  "dark"),
    "golem":           (30, "dark"),
    "witch":           (12, "dark"),
    "lava_hound":      (30, "dark"),
    "bowler":          (6,  "dark"),
    "ice_golem":       (15, "dark"),
    "head_hunter":     (6,  "dark"),
    "apprentice_warden": (20, "dark"),
}

# Tên cũ / biến thể -> key chuẩn
TROOP_ALIASES = {
    "hogrider":          "hog_rider",
    "hog":               "hog_rider",
    "headhunter":        "head_hunter",
    "lava":              "lava_hound",
    "yetti":             "yeti",
    "e_drag":            "electro_dragon",
    "edrag":             "electro_dragon",
    "edragon":           "electro_dragon",
    "electro_drag":      "electro_dragon",
    "electrodragon":     "electro_dragon",
    "wallbreaker":       "wall_breaker",
    "baby":              "baby_dragon",
    "apprentice":        "apprentice_warden",
    "dragonrider":       "dragon_rider",
    "electrotitan":      "electro_titan",
    "rootrider":         "root_rider",
}

# Key chuẩn -> tên file icon (chỉ các trường hợp KHÁC key)
TROOP_ICON_FILES = {
    "lava_hound": "lava",
    "yeti":       "yetti",
}

# ═══════════════════════════════════════════════════════════════
# SPELLS
# ═══════════════════════════════════════════════════════════════
SPELLS = {
    "lightning":     (1, "elixir"),
    "heal":          (2, "elixir"),
    "rage":          (2, "elixir"),
    "jump":          (2, "elixir"),
    "freeze":        (1, "elixir"),
    "clone":         (3, "elixir"),
    "invi":          (1, "elixir"),
    "recall":        (1, "elixir"),
    "resurrect":     (2, "elixir"),
    "poison":        (1, "dark"),
    "eq":            (1, "dark"),
    "haste":         (1, "dark"),
    "skelly":        (1, "dark"),
    "bats":          (1, "dark"),
    "over_growth":   (3, "dark"),
}

SPELL_ALIASES = {
    "healing":      "heal",
    "healing_spell": "heal",
    "invisibility": "invi",
    "invis":        "invi",
    "earthquake":   "eq",
    "quake":        "eq",
    "skeleton":     "skelly",
    "skeleton_spell": "skelly",
    "bat":          "bats",
    "bat_spell":    "bats",
    "revive":       "resurrect",
    "revive_spell": "resurrect",
    "overgrowth":   "over_growth",
    "overgrowth_spell": "over_growth",
}

SPELL_ICON_FILES = {}   # key đã trùng tên file

# ═══════════════════════════════════════════════════════════════
# SIEGE MACHINES
# ═══════════════════════════════════════════════════════════════
SIEGE = {
    "slammer":         (1, "siege"),   # Stone Slammer
    "wall_wrecker":    (1, "siege"),
    "blimp":           (1, "siege"),   # Battle Blimp
    "barracks":        (1, "siege"),   # Siege Barracks
    "log_launcher":    (1, "siege"),
    "flame_flinger":   (1, "siege"),
    "battle_drill":    (1, "siege"),
    "troop_launcher":  (1, "siege"),
}

SIEGE_ALIASES = {
    "battle_blimp":    "blimp",
    "siege_barracks":  "barracks",
    "stone_slammer":   "slammer",
    "slam":            "slammer",
    "wrecker":         "wall_wrecker",
    "flameflinger":    "flame_flinger",
    "loglauncher":     "log_launcher",
    "battledrill":     "battle_drill",
    "trooplauncher":   "troop_launcher",
}

SIEGE_ICON_FILES = {}   # key đã trùng tên file


# ═══════════════════════════════════════════════════════════════
# TRAIN TEMPLATES — tên file trong Templates/Smart_Auto_train/to_train
# ═══════════════════════════════════════════════════════════════
_TRAIN_TROOP_OVERRIDES = {
    "head_hunter": "Headhunter",
    "lava_hound":  "LavaHound",
    "yeti":        "Yeti",
    "healer":      "Healer",
    "pekka":       "icon_pekka",
}

_TRAIN_SPELL_OVERRIDES = {
    "heal":        "HealingSpell",
    "invi":        "InvisibilitySpell",
    "eq":          "EarthquakeSpell",
    "skelly":      "SkeletonSpell",
    "bats":        "BatSpell",
    "over_growth": "OvergrowthSpell",
    "resurrect":   "ReviveSpell",
    "lightning":   "LightningSpell",
    "rage":        "RageSpell",
    "freeze":      "FreezeSpell",
    "jump":        "JumpSpell",
    "clone":       "CloneSpell",
    "poison":      "PoisonSpell",
    "haste":       "HasteSpell",
    "recall":      "RecallSpell",
}

_TRAIN_SIEGE_OVERRIDES = {
    "slammer":        "StoneSlammer",
    "wall_wrecker":   "WallWrecker",
    "blimp":          "BattleBlimp",
    "barracks":       "SiegeBarracks",
    "log_launcher":   "LogLauncher",
    "flame_flinger":  "FlameFlinger",
    "battle_drill":   "BattleDrill",
    "troop_launcher": "TroopLauncher",
}


def _pascal(key):
    return "".join(part.capitalize() for part in key.split("_") if part)


def train_template_file(name, kind="troop"):
    """Tên file (không .png) trong to_train cho 1 key bất kỳ."""
    if kind == "spell":
        key = canonical_spell(name)
        return _TRAIN_SPELL_OVERRIDES.get(key, _pascal(key) + "Spell")
    if kind == "siege":
        key = canonical_siege(name)
        return _TRAIN_SIEGE_OVERRIDES.get(key, _pascal(key))
    key = canonical_troop(name)
    return _TRAIN_TROOP_OVERRIDES.get(key, _pascal(key))


# ───────────────────── canonical helpers ─────────────────────
def canonical_troop(name):
    key = _norm(name)
    return TROOP_ALIASES.get(key, key)


def canonical_spell(name):
    key = _norm(name)
    return SPELL_ALIASES.get(key, key)


def canonical_siege(name):
    key = _norm(name)
    return SIEGE_ALIASES.get(key, key)


def troop_icon_file(name):
    """Tên file icon (không .png) trong thư mục Army Troops."""
    key = canonical_troop(name)
    return TROOP_ICON_FILES.get(key, key)


def spell_icon_file(name):
    key = canonical_spell(name)
    return SPELL_ICON_FILES.get(key, key)


def siege_icon_file(name):
    key = canonical_siege(name)
    return SIEGE_ICON_FILES.get(key, key)


# ───────────────────── space / listing ─────────────────────
def get_troop_space(name):
    return TROOPS.get(canonical_troop(name), (0, ""))[0]


def get_spell_space(name):
    return SPELLS.get(canonical_spell(name), (0, ""))[0]


def get_siege_space(name):
    return SIEGE.get(canonical_siege(name), (1, "siege"))[0]


def get_troop_category(name):
    return TROOPS.get(canonical_troop(name), (0, ""))[1]


def list_troops(category=None):
    if category:
        return [k for k, (_, cat) in TROOPS.items() if cat == category]
    return list(TROOPS.keys())


def list_spells(category=None):
    if category:
        return [k for k, (_, cat) in SPELLS.items() if cat == category]
    return list(SPELLS.keys())
