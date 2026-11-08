# ==== src/core/army_presets.py ====
import json
import os
import sys

from core.paths import SRC_DIR as BASE_DIR

PRESETS_PATH = os.path.join(BASE_DIR, "army_presets.json")

from core.troop_registry import canonical_siege, canonical_spell, canonical_troop

DEFAULT_SIDE = "Ngẫu nhiên"

VALID_SIDES = [
    "Ngẫu nhiên",
    "Trên Trái (TL)",
    "Trên Phải (TR)",
    "Dưới Trái (BL)",
    "Dưới Phải (BR)",
    "Nửa Trên (TL + TR)",
    "Nửa Dưới (BL + BR)",
    "Cả 4 hướng (+)",
]

DEFAULT_PRESETS = {
    "presets": {
        "Dragon Balloon": {
            "troops": {"dragon": 9, "balloon": 4},
            "spells": {"rage": 5, "freeze": 1},
            "siege": {"slammer": 1},
            "side": "Ngẫu nhiên",
        },
        "E-Drag Rush": {
            "troops": {"electro_dragon": 7, "balloon": 2},
            "spells": {"rage": 6, "freeze": 1},
            "siege": {"slammer": 1},
            "side": "Ngẫu nhiên",
        },
    },
    "active": "Dragon Balloon",
}


def _clean_counts(raw, canon):
    out = {}
    if not isinstance(raw, dict):
        return out
    for name, count in raw.items():
        try:
            count = int(count)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        key = canon(name)
        out[key] = out.get(key, 0) + count
    return out


def normalize_recipe(recipe):
    recipe = recipe if isinstance(recipe, dict) else {}
    side = recipe.get("side") or recipe.get("attack_side") or DEFAULT_SIDE
    if side not in VALID_SIDES:
        side = DEFAULT_SIDE
    return {
        "troops": _clean_counts(recipe.get("troops"), canonical_troop),
        "spells": _clean_counts(recipe.get("spells"), canonical_spell),
        "siege": _clean_counts(recipe.get("siege"), canonical_siege),
        "side": side,
    }


def _normalize_data(data):
    if not isinstance(data, dict):
        data = {}
    presets = data.get("presets")
    if not isinstance(presets, dict):
        presets = {}
    data["presets"] = {name: normalize_recipe(r) for name, r in presets.items()}
    if data.get("active") not in data["presets"]:
        data["active"] = next(iter(data["presets"]), "")
    return data


def _ensure_file():
    if not os.path.exists(PRESETS_PATH):
        with open(PRESETS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PRESETS, f, indent=2, ensure_ascii=False)


def load_presets():
    _ensure_file()
    try:
        with open(PRESETS_PATH, "r", encoding="utf-8") as f:
            return _normalize_data(json.load(f))
    except Exception as e:
        print(f"[PRESETS] load failed: {e}")
        return {"presets": {}, "active": ""}


def save_presets(data):
    try:
        data = _normalize_data(data)
        with open(PRESETS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[PRESETS] save failed: {e}")
        return False


def get_preset(name):
    data = load_presets()
    return data["presets"].get(name)


def get_active_preset():
    data = load_presets()
    active = data.get("active", "")
    return active, data["presets"].get(active)
