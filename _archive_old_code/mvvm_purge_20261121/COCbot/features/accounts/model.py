"""Accounts feature domain model (pure Python, no Qt)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from COCbot.core.config.defaults import MAX_ACCOUNTS
from COCbot.core.config.paths import get_project_paths
from COCbot.core.errors import AccountError
from COCbot.core.ports import AccountStorePort
from COCbot.models.account import AccountProfileInfo, AccountsSnapshot


def default_switch_config() -> dict[str, Any]:
    """Return the default auto-switch configuration."""
    return {
        "enabled": False,
        "consecutive_attacks": 2,
        "use_attack_limit": True,
        "use_time_schedule": False,
        "use_storage_full": False,
        "storage_full_wait_minutes": 10,
        "storage_full_threshold": 0.85,
        "storage_full_min_matches": 1,
        "schedule_minutes": 60,
        "last_switch_ts": 0,
        "total_accounts": 2,
        "current_profile": "",
        "accounts": [
            {"enabled": index < 2, "profile": "", "attacks": 0}
            for index in range(MAX_ACCOUNTS)
        ],
    }


class AccountsModel:
    """Manage shared_prefs profiles and the auto-switch config file."""

    def __init__(
        self,
        manager: AccountStorePort,
        switch_config_path: Path | str | None = None,
    ) -> None:
        """Wrap an account store and the switch config location."""
        self._manager = manager
        self._path = (
            Path(switch_config_path)
            if switch_config_path is not None
            else get_project_paths().profiles_dir / "switch_accounts.json"
        )

    @property
    def path(self) -> Path:
        """Return the auto-switch config path."""
        return self._path

    def load_switch_config(self) -> dict[str, Any]:
        """Load the switch config, merging it with defaults."""
        config = default_switch_config()
        if not self._path.is_file():
            return config
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return config
        if not isinstance(raw, dict):
            return config
        config.update({key: raw[key] for key in config if key in raw})
        accounts = raw.get("accounts")
        if isinstance(accounts, list):
            for index, item in enumerate(accounts[:MAX_ACCOUNTS]):
                if not isinstance(item, dict):
                    continue
                config["accounts"][index] = {
                    "enabled": bool(item.get("enabled", False)),
                    "profile": str(item.get("profile", "")),
                    "attacks": int(item.get("attacks", 0) or 0),
                }
        return config

    def save_switch_config(self, config: Mapping[str, Any]) -> None:
        """Persist the switch config atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(dict(config), ensure_ascii=False, indent=2)
        temp = self._path.with_suffix(self._path.suffix + ".tmp")
        temp.write_text(payload, encoding="utf-8")
        temp.replace(self._path)

    def list_profiles(self) -> list[AccountProfileInfo]:
        """Return every shared_prefs profile on disk."""
        profiles: list[AccountProfileInfo] = []
        for item in self._manager.list_profiles():
            profiles.append(
                AccountProfileInfo(
                    name=str(item.get("name", "")),
                    safe_name=str(item.get("safe_name", "")),
                    saved_at=str(item.get("saved_at", "")),
                    android_id=str(item.get("android_id", "")),
                    files=int(item.get("files", 0) or 0),
                    exists=bool(item.get("exists", False)),
                )
            )
        return profiles

    def root_label(self) -> str:
        """Return a display-safe ADB root label."""
        try:
            return self._manager.root_label()
        except Exception as exc:
            return f"ADB: {type(exc).__name__}"

    def snapshot(self) -> AccountsSnapshot:
        """Return profiles plus the current switch configuration."""
        config = self.load_switch_config()
        return AccountsSnapshot(
            profiles=tuple(self.list_profiles()),
            current_profile=str(config.get("current_profile", "")),
            root_label=self.root_label(),
            config=config,
        )

    def pull(self, name: str) -> None:
        """Save the current game account into *name*."""
        clean = name.strip()
        if not clean:
            raise AccountError("Profile name cannot be empty")
        self._manager.pull_profile(clean, close_game=True)

    def push(self, name: str, current_profile: str = "") -> None:
        """Restore *name* into the game."""
        clean = name.strip()
        if not clean:
            raise AccountError("Select a profile to push")
        current = current_profile.strip() or str(
            self.load_switch_config().get("current_profile", "")
        )
        self._manager.push_profile(clean, current_profile=current, close_game=True)
        self.set_current_profile(clean)

    def switch(self, target: str, current_profile: str = "") -> None:
        """Switch from the current account to *target*."""
        clean = target.strip()
        if not clean:
            raise AccountError("Select a profile to switch to")
        current = current_profile.strip() or str(
            self.load_switch_config().get("current_profile", "")
        )
        self._manager.switch_profile(current, clean)
        self.set_current_profile(clean)

    def delete(self, name: str) -> None:
        """Delete the stored profile."""
        clean = name.strip()
        if not clean:
            raise AccountError("Select a profile to delete")
        self._manager.delete_profile(clean)

    def set_current_profile(self, name: str) -> dict[str, Any]:
        """Update the current profile in the switch config."""
        config = self.load_switch_config()
        config["current_profile"] = name
        self.save_switch_config(config)
        return config

    def update_auto_switch(self, enabled: bool, attacks: int) -> dict[str, Any]:
        """Update the two most common auto-switch options."""
        config = self.load_switch_config()
        config["enabled"] = bool(enabled)
        config["consecutive_attacks"] = max(1, int(attacks))
        config["use_attack_limit"] = True
        self.save_switch_config(config)
        return config
