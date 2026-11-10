"""Unit tests for the typed configuration schema and JSON persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from COCbot.core.config import AppConfig, EmulatorConfig, load_config, save_config
from COCbot.models.enums import EmulatorType

LEGACY_SAMPLE = {
    "gold_threshold": 120000,
    "elixir_threshold": 90000,
    "dark_elixir_threshold": 1200,
    "upgrade_wall": True,
    "wall_level": 11,
    "wall_gold_threshold": 4000000,
    "wall_elixir_threshold": 3000000,
    "upgrade_hero": True,
    "hero_priorities": ["Queen", "King"],
    "upgrade_defense": False,
    "defense_priorities": [],
    "upgrade_army": True,
    "army_priorities": ["Lab"],
    "upgrade_resource": False,
    "resource_priorities": [],
    "upgrade_other": True,
    "other_buildings": ["Clan Castle"],
    "request_troops": False,
    "attack": "ElectroDragon_Attack",
    "recipe_name": "edrag",
    "recipe": {
        "troops": {"electro_dragon": 6, "balloon": 2, "bad": 0},
        "spells": {"rage": 5},
        "siege": {"slammer": 1},
        "side": "Trên Trái (TL)",
    },
    "attack_side": "Trên Trái (TL)",
    "check_troops": True,
    "train_mode": "quick",
    "quick_slot": 3,
    "enable_clan_games": True,
    "enable_clan_capital": True,
    "capital_hall_level": 10,
    "enable_stats": True,
    "redline_model": "models/custom.pt",
    "redline_offset_ratio": 0.5,
    "auto_capture_dataset": False,
    "auto_capture_dir": "datasets/custom",
    "auto_capture_max_files": 50,
    "attack_sides": ["Trên Trái (TL)", "Ngẫu nhiên"],
}


class ConfigSchemaTests(unittest.TestCase):
    """Verify legacy JSON mapping and round-trip behavior."""

    def test_defaults(self) -> None:
        config = AppConfig()
        self.assertEqual(config.emulator.emulator_type, EmulatorType.MEMU)
        self.assertEqual(config.emulator.host, "127.0.0.1:21503")
        self.assertEqual(config.training.quick_slot, 1)
        self.assertTrue(config.clan.request_troops)

    def test_from_legacy_mapping(self) -> None:
        config = AppConfig.from_legacy_dict(LEGACY_SAMPLE)
        self.assertEqual(config.resources.gold, 120000)
        self.assertEqual(config.resources.dark_elixir, 1200)
        self.assertTrue(config.upgrades.wall.enabled)
        self.assertEqual(config.upgrades.wall.level, 11)
        self.assertEqual(config.upgrades.hero.priorities, ["Queen", "King"])
        self.assertEqual(config.upgrades.other.priorities, ["Clan Castle"])
        self.assertEqual(config.attack.name, "ElectroDragon_Attack")
        self.assertEqual(config.attack.side, "Trên Trái (TL)")
        self.assertEqual(config.attack.recipe.name, "edrag")
        self.assertEqual(config.attack.recipe.troops, {"electro_dragon": 6, "balloon": 2})
        self.assertTrue(config.attack.check_troops)
        self.assertEqual(config.training.mode, "quick")
        self.assertEqual(config.vision.redline_model, "models/custom.pt")
        self.assertFalse(config.auto_capture.enabled)
        self.assertEqual(config.auto_capture.max_files, 50)
        self.assertEqual(config.attack.sides, ["Trên Trái (TL)", "Ngẫu nhiên"])

    def test_round_trip(self) -> None:
        config = AppConfig.from_legacy_dict(LEGACY_SAMPLE)
        payload = config.to_dict()
        again = AppConfig.from_legacy_dict(payload)
        self.assertEqual(again.resources, config.resources)
        self.assertEqual(again.upgrades, config.upgrades)
        self.assertEqual(again.attack, config.attack)
        self.assertEqual(again.auto_capture, config.auto_capture)
        self.assertEqual(again.logging, config.logging)

    def test_missing_recipe_is_tolerated(self) -> None:
        config = AppConfig.from_legacy_dict({"attack": "Dragon_Attack"})
        self.assertEqual(config.attack.recipe.side, "Ngẫu nhiên")
        self.assertEqual(config.attack.sides, ["Ngẫu nhiên"])

    def test_emulator_host_defaults_by_type(self) -> None:
        self.assertEqual(
            EmulatorConfig(emulator_type=EmulatorType.LDPLAYER).host,
            "127.0.0.1:5555",
        )
        self.assertEqual(
            EmulatorConfig(emulator_type=EmulatorType.BLUESTACKS).host,
            "127.0.0.1:5556",
        )
        self.assertEqual(
            EmulatorConfig(emulator_type=EmulatorType.CUSTOM, host="10.0.0.5:5555").host,
            "10.0.0.5:5555",
        )


class ConfigPersistenceTests(unittest.TestCase):
    """Verify atomic save/load and malformed-file fallback."""

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            config = AppConfig.from_legacy_dict(LEGACY_SAMPLE)
            save_config(config, path)
            self.assertTrue(path.is_file())

            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["gold_threshold"], 120000)
            self.assertEqual(raw["attack_side"], "Trên Trái (TL)")

            loaded = load_config(path)
            self.assertEqual(loaded.to_dict(), config.to_dict())

    def test_missing_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            loaded = load_config(Path(temp_dir) / "missing.json")
            self.assertEqual(loaded, AppConfig())

    def test_malformed_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_config(path), AppConfig())


if __name__ == "__main__":
    unittest.main()
