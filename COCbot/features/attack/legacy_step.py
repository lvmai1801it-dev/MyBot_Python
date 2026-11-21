"""Legacy attack step: a faithful port of the proven pre-MVVM attack flow.

Rather than reimplementing the battle pipeline, this CycleStep drives the
exact sequence the legacy engine has farmed with successfully:

    search_attack -> wait_for_scout_screen -> extract_resources ->
    threshold gate (search_next until gold AND elixir AND dark pass) ->
    run_attack (ONNX redline + mask sanitize + verify-and-redrop + final
    sweep) -> wait_battle_end -> stars/loot stats -> return_home

The body mirrors ``app/bootstrap.one_cycle``'s attack section line for line
(scout retry, connection recovery, loot log, stats bookkeeping) so the
behaviour is identical; only the stop/pause plumbing is bridged to the
orchestrator session, and account switching stays with the legacy engine.
"""

from __future__ import annotations

import time
from typing import Any

from COCbot.app.orchestrator import CycleContext, StepResult
from COCbot.models.enums import BotPhase


class LegacyAttackStep:
    """Run one complete legacy attack through the clean orchestrator."""

    def __init__(
        self,
        config_store: Any,
        host: str,
        village_idx: int = 1,
        execute: bool = False,
    ) -> None:
        """Create the step; real input only when *execute* is true."""
        self._store = config_store
        self._host = host
        self._village_idx = village_idx
        self._execute = execute

    @property
    def name(self) -> str:
        """Return the stable step name."""
        return "attack"

    def run(self, context: CycleContext) -> StepResult:
        """Search, gate on loot, attack once, then return home."""
        if not self._execute:
            return StepResult(
                True,
                "Attack step skipped (dry run; set MYBOT_LIVE_ATTACK=1)",
                phase=BotPhase.SEARCHING,
                data={"skipped": True},
            )

        import threading

        from COCbot.app import state
        from COCbot.attack.api import run_attack
        from COCbot.game.account.boot_recovery import boot_recovery as _recover
        from COCbot.game.battle.helpers import (
            connection_popup_visible,
            is_next_button_present,
            search_attack,
            search_next,
            wait_battle_end,
            wait_for_scout_screen,
        )
        from COCbot.game.battle.target import extract_resources
        from COCbot.platform.adb_utils import return_home

        cfg = dict(self._store.get().to_dict())
        thresholds = (
            int(cfg.get("gold_threshold", 0) or 0),
            int(cfg.get("elixir_threshold", 0) or 0),
            int(cfg.get("dark_elixir_threshold", 0) or 0),
        )
        print(
            f"[INFO] Search criteria -> Gold >= {thresholds[0]}, "
            f"Elixir >= {thresholds[1]}, Dark >= {thresholds[2]}"
        )

        # Bridge the legacy module-level signals to this session for the
        # duration of the attack; pause is handled at step boundaries.
        saved_stop = state.stop_event
        saved_pause = state.pause_event
        state.host = self._host
        state.stop_event = context.session.stop_event
        state.pause_event = threading.Event()
        state.pause_event.set()
        try:
            print("[INFO] Searching for base to attack...")
            search_attack()

            while not state.stop_event.is_set():
                if connection_popup_visible():
                    print("[WARN] Connection lost during evaluation -> recovering")
                    _recover()
                    return StepResult(False, "Connection lost; recovered")

                if not wait_for_scout_screen():
                    print("[WARN] Scouting UI not detected -> recovering")
                    _recover()
                    return StepResult(False, "Scout screen not detected")

                for attempt in range(1, 4):
                    if is_next_button_present():
                        break
                    print(f"[WARN] Next button missing - retrying ({attempt}/3)")
                    time.sleep(2)
                else:
                    print("[WARN] Next button still missing - triggering recovery")
                    _recover()
                    return StepResult(False, "Next button missing; recovered")

                gold_raw, elixir_raw, dark_raw, _scout_img = extract_resources(
                    return_image=True
                )
                gold, elixir, dark = int(gold_raw), int(elixir_raw), int(dark_raw)
                print(f"[LOOT] GOLD: {gold}  ELIXIR: {elixir}  DARK_ELIXIR: {dark}")

                good_base = (
                    gold >= thresholds[0]
                    and elixir >= thresholds[1]
                    and dark >= thresholds[2]
                )
                if good_base:
                    print("[INFO] Good base found -> attacking")
                    run_attack(cfg)
                    wait_battle_end()

                    data = {"gold": gold, "elixir": elixir, "dark_elixir": dark}
                    if cfg.get("enable_stats", False):
                        stars = self._record_stats(gold, elixir, dark)
                        data["stars"] = stars

                    return_home()
                    print("[INFO] Attack complete")
                    return StepResult(
                        True,
                        f"Attacked a base with {gold}/{elixir}/{dark} loot",
                        phase=BotPhase.ATTACKING,
                        data=data,
                    )

                print("[INFO] Loot below threshold -> next")
                search_next()

            return StepResult(False, "Attack aborted", phase=BotPhase.SEARCHING)
        finally:
            state.stop_event = saved_stop
            state.pause_event = saved_pause

    def _record_stats(self, gold: int, elixir: int, dark: int) -> int:
        """Port of the legacy stats block: stars + gained resources."""
        from COCbot.app.stats import _load_stats_from_disk, _stats_file_path
        from COCbot.game.battle.helpers import get_stars_from_screen, gain_resources

        try:
            stars = get_stars_from_screen()
        except Exception:
            stars = 0
        gained_gold, gained_elixir, gained_dark = gain_resources(stars)

        stats = _load_stats_from_disk(self._village_idx)
        stats["gold"] = stats.get("gold", 0) + gained_gold
        stats["elixir"] = stats.get("elixir", 0) + gained_elixir
        stats["de"] = stats.get("de", 0) + gained_dark
        stats["attacks"] = stats.get("attacks", 0) + 1
        key = str(stars)
        stars_block = stats.setdefault("stars", {"0": 0, "1": 0, "2": 0, "3": 0})
        stars_block[key] = stars_block.get(key, 0) + 1
        stats["stars"] = stars_block
        stats["last_update_ts"] = time.time()

        import json

        with open(_stats_file_path(self._village_idx), "w", encoding="utf-8") as handle:
            json.dump(stats, handle, indent=2)
        return stars
