"""Configuration for account switching (Supercell ID / shared_prefs)."""

from __future__ import annotations

import json
from pathlib import Path

from COCbot.app.paths import SRC_DIR

CONFIG_PATH = Path(SRC_DIR) / "profiles" / "switch_accounts.json"
MAX_ACCOUNTS = 16
ACCOUNTS_PER_PAGE = 8


def default_config() -> dict:
    return {
        "enabled": False,
        "mode": "supercell",
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
        "current_slot": 1,
        "accounts": [
            {"enabled": i < 2, "profile": "", "attacks": 0}
            for i in range(MAX_ACCOUNTS)
        ],
    }


def load_switch_config() -> dict:
    cfg = default_config()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            cfg.update({k: data[k] for k in cfg if k in data})
            accounts = data.get("accounts")
            if isinstance(accounts, list):
                for i, item in enumerate(accounts[:MAX_ACCOUNTS]):
                    if isinstance(item, dict):
                        cfg["accounts"][i] = {
                            "enabled": bool(item.get("enabled", False)),
                            "profile": str(item.get("profile", "")),
                            "attacks": int(item.get("attacks", 0) or 0),
                        }
    except Exception:
        pass
    return cfg


def save_switch_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def enabled_profiles(cfg: dict) -> list[str]:
    return [
        a["profile"] for a in cfg.get("accounts", [])
        if a.get("enabled") and a.get("profile")
    ]
