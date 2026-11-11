"""Upgrade execution: buildings until maxed, one army/pet upgrade at a time."""

from __future__ import annotations

from dataclasses import dataclass

from COCbot.core.config.schema import UpgradeConfig
from COCbot.core.ports import LoggerPort
from COCbot.features.village.planner import plan_upgrades
from COCbot.features.village.upgrades import HeroDefenseUpgrader

MAX_ATTEMPTS_PER_TARGET = 8


@dataclass(frozen=True)
class UpgradeRunResult:
    """Outcome of one upgrade run."""

    ok: bool
    upgraded: tuple[str, ...]
    builders_left: int | None
    message: str
    needs_loot: bool = False


class UpgradeRunner:
    """Drive the Build panel according to the planner capacities."""

    def __init__(
        self,
        upgrader: HeroDefenseUpgrader,
        logger: LoggerPort | None = None,
    ) -> None:
        """Create the runner around the panel upgrader."""
        self._upgrader = upgrader
        self._logger = logger

    def _log(self, level: str, message: str) -> None:
        """Emit a log line when a logger was supplied."""
        if self._logger is not None:
            getattr(self._logger, level)(message)

    def run(
        self,
        config: UpgradeConfig,
        builders_available: int,
        execute: bool = False,
        max_per_target: int = MAX_ATTEMPTS_PER_TARGET,
    ) -> UpgradeRunResult:
        """Upgrade buildings until maxed, then one army/pet upgrade."""
        plan = plan_upgrades(config, builders_available)
        if not plan.order:
            return UpgradeRunResult(
                True,
                (),
                plan.budget,
                "No enabled upgrades for the available builders",
            )
        if not execute:
            return UpgradeRunResult(
                True,
                plan.order,
                plan.budget,
                "Dry run: would upgrade " + ", ".join(plan.order),
            )

        left = plan.budget
        upgraded: list[str] = []
        for name in plan.order:
            repeat = name not in plan.single_slot
            if repeat and left <= 0:
                break
            attempts = max(1, max_per_target) if repeat else 1
            for _attempt in range(attempts):
                result = self._upgrader.upgrade_listed(name, execute=True)
                if result.executed:
                    upgraded.append(name)
                    if repeat:
                        left -= 1
                        self._log("info", f"Upgraded {name}; builders left: {left}")
                        if left <= 0:
                            break
                    continue
                if result.needs_loot:
                    return UpgradeRunResult(
                        True,
                        tuple(upgraded),
                        left,
                        result.message,
                        needs_loot=True,
                    )
                if "no longer listed" in result.message:
                    break
                self._upgrader.dismiss(execute=True)
                return UpgradeRunResult(
                    False,
                    tuple(upgraded),
                    left,
                    result.message,
                )
            if repeat and left <= 0:
                break
        self._upgrader.dismiss(execute=True)
        return UpgradeRunResult(
            True,
            tuple(upgraded),
            left,
            f"Upgraded {len(upgraded)} target(s); builders left: {left}",
        )
