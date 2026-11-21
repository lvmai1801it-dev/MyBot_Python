"""Account profile and rotation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from COCbot.models.enums import AccountSwitchMode


@dataclass(frozen=True)
class AccountProfile:
    """One shared_prefs profile that the bot can switch to."""

    name: str
    path: str = ""
    tag: str = ""
    town_hall: int = 0
    level: int = 0
    last_used: float = 0.0

    def display_name(self) -> str:
        """Return a compact label for the account switcher UI."""
        if self.tag:
            return f"{self.name} ({self.tag})"
        return self.name


@dataclass(frozen=True)
class AccountSwitchState:
    """Current account-rotation configuration and counters."""

    mode: AccountSwitchMode = AccountSwitchMode.OFF
    current: str = ""
    accounts_per_page: int = 1
    max_accounts: int = 10
    attacks_done: int = 0
    attacks_per_account: int = 0

    def should_rotate(self) -> bool:
        """Return ``True`` when the per-account attack quota is reached."""
        if self.mode is AccountSwitchMode.OFF:
            return False
        if self.attacks_per_account <= 0:
            return False
        return self.attacks_done >= self.attacks_per_account


@dataclass(frozen=True)
class AccountProfileInfo:
    """A shared_prefs profile discovered on disk."""

    name: str
    safe_name: str = ""
    saved_at: str = ""
    android_id: str = ""
    files: int = 0
    exists: bool = True

    def display_text(self) -> str:
        """Return a compact label for the profile picker."""
        if self.saved_at:
            return f"{self.name} · {self.saved_at} · {self.files} files"
        return f"{self.name} · {self.files} files"


@dataclass(frozen=True)
class AccountsSnapshot:
    """Profiles plus the current switch configuration."""

    profiles: tuple[AccountProfileInfo, ...] = ()
    current_profile: str = ""
    root_label: str = ""
    config: Mapping[str, Any] = field(default_factory=dict)
