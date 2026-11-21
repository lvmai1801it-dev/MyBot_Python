"""Farm-loop upgrade hook for the legacy GUI.

Ported from the retired MVVM ``LegacyEngine`` so the auto-upgrade feature
keeps working in ``python run.py``: the ticked Buildings & Heroes / Army /
Equipment / Pets rows in the Village tab run every cycle while a builder
is free, and wall upgrades go through the Build panel with the builder the
buildings left behind.

The hook is installed on ``state.upgrade_hook`` by ``MainWindow.on_start``
and cleared on stop/exit; ``one_cycle`` calls it right after the home check
and skips the old map-scanning wall routine while it is active.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from COCbot.app import state

# Per-host cache: ADB/capture/upgrader/runner are reused across cycles.
_SERVICES: dict[str, Tuple[Any, Any, Any, Any]] = {}


def _services(host: str):
    """Return (reader, runner, upgrader) for *host*, building them once."""
    if host in _SERVICES:
        return _SERVICES[host]

    from COCbot.core.adb import AdbClient
    from COCbot.core.config import load_config
    from COCbot.core.vision import ScreenCapture
    from COCbot.features.village.resources import ResourceReader, regions_from_config
    from COCbot.features.village.runner import UpgradeRunner
    from COCbot.features.village.upgrades import HeroDefenseUpgrader

    adb = AdbClient(host=host)
    adb.connect(host, timeout=5.0)
    capture = ScreenCapture(adb)
    config = load_config()
    reader = ResourceReader(
        capture,
        glm_server=(
            config.vision.ocr_server
            if config.vision.ocr_engine in ("auto", "glm")
            else None
        ),
        regions=regions_from_config(config.vision.ocr_regions),
        adb=adb,
    )
    upgrader = HeroDefenseUpgrader(adb, capture)
    runner = UpgradeRunner(upgrader)
    _SERVICES[host] = (reader, runner, upgrader)
    return _SERVICES[host]


def run_upgrades() -> None:
    """Run the ticked upgrades when a builder is free (cycle hook)."""
    host = getattr(state, "host", None)
    if not host:
        print("[UPGRADE] no ADB host yet; skipping")
        return

    from COCbot.core.config import load_config
    from COCbot.features.village.runner import UpgradeRunResult

    config = load_config()
    upgrades = config.upgrades
    reader, runner, upgrader = _services(host)

    groups = (
        upgrades.buildings,
        upgrades.army,
        upgrades.equipment,
        upgrades.pets,
    )
    if not any(group.enabled or group.priorities for group in groups):
        print("No upgrade targets selected — tick targets in Village and Save")
        return

    try:
        snapshot = reader.read()
    except Exception as exc:
        print(f"[UPGRADE] builder check failed: {type(exc).__name__}: {exc}")
        return
    builders = snapshot.builders_available
    if builders is None:
        print("[UPGRADE] could not read the builder count")
        return
    if builders <= 0:
        print("No free builder — skipping upgrades")
        return

    print(f"[UPGRADE] {builders} builder(s) free — upgrading")
    gold = snapshot.gold
    elixir = snapshot.elixir
    result: UpgradeRunResult = runner.run(upgrades, builders, execute=True)
    if result.needs_loot:
        print("Not enough loot for the next upgrade — attacking to earn more")
    else:
        print(result.message)

    left = result.builders_left if result.builders_left is not None else builders
    if upgrades.wall.enabled and left > 0:
        wall_result = upgrader.upgrade_walls_via_panel(
            execute=True, gold=gold, elixir=elixir
        )
        print(wall_result.message)


def install() -> None:
    """Attach the hook so one_cycle runs upgrades every cycle."""
    state.upgrade_hook = run_upgrades


def uninstall() -> None:
    """Detach the hook (called on stop/exit)."""
    state.upgrade_hook = None
    _SERVICES.clear()


def is_installed() -> bool:
    """Return True when the hook is attached."""
    return getattr(state, "upgrade_hook", None) is not None
