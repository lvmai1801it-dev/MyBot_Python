# ==== COCbot/gui/settings_store.py ====
"""Load/save runtime settings."""
import json
import os

from COCbot.gui.constants import CFG_PATH


def load_settings():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "gold_threshold": 65000,
        "elixir_threshold": 65000,
        "dark_elixir_threshold": 500,
        "upgrade_wall": False,
        "wall_level": 5,
        "wall_gold_threshold": 5000000,
        "wall_elixir_threshold": 5000000,
        "upgrade_hero": False,
        "hero_priorities": [],
        "upgrade_defense": False,
        "defense_priorities": [],
        "upgrade_army": False,
        "army_priorities": [],
        "upgrade_resource": False,
        "resource_priorities": [],
        "upgrade_other": False,
        "other_buildings": [],
        "enable_clan_games": False,
        "request_troops": True,
        "attack": "Dragon_Attack",
        "train_mode": "smart",
        "quick_slot": 1,
        "enable_stats": False,
        "enable_clan_capital": False,
        "capital_hall_level": 9,
    }


def save_settings(cfg: dict):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] could not save settings: {e}")
