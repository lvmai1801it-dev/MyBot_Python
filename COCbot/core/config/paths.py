"""Filesystem path resolution for source and frozen builds.

The single source of truth for every directory used at runtime. Feature code
must obtain paths from here (or from ``AppConfig``) instead of hard-coding
strings.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _is_project_root(candidate: Path) -> bool:
    """Return ``True`` when *candidate* contains the expected project markers."""
    markers = ("Templates", "settings.json", "COCbot", "run.py")
    return any((candidate / marker).exists() for marker in markers)


def resolve_src_dir() -> Path:
    """Locate the project ``src`` directory for source and frozen runs."""
    override = os.environ.get("MYBOT_SRC_DIR")
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    current = Path(__file__).resolve()
    for parent in list(current.parents)[:6]:
        if _is_project_root(parent):
            return parent
    return current.parents[3]


@dataclass(frozen=True)
class ProjectPaths:
    """Resolved absolute paths used by the application."""

    src_dir: Path
    cocbot_dir: Path
    templates_dir: Path
    models_dir: Path
    datasets_dir: Path
    walls_dir: Path
    profiles_dir: Path
    images_dir: Path
    debug_dir: Path
    logs_dir: Path
    adb_dir: Path
    adb_bin: Path
    attacks_dir: Path
    settings_json: Path
    army_presets_json: Path
    autohotkey_exe: Path

    def ensure_dir(self, path: Path) -> Path:
        """Create *path* (including parents) and return it."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_runtime_dirs(self) -> None:
        """Create writable runtime directories used by the bot."""
        for path in (self.logs_dir, self.debug_dir, self.datasets_dir):
            self.ensure_dir(path)

    def as_dict(self) -> dict[str, str]:
        """Return every path as a JSON-friendly string mapping."""
        return {
            field_name: str(getattr(self, field_name))
            for field_name in self.__dataclass_fields__
        }


@lru_cache(maxsize=1)
def get_project_paths() -> ProjectPaths:
    """Return the cached :class:`ProjectPaths` for the current process."""
    src = resolve_src_dir()
    cocbot = src / "COCbot"

    adb_dir = src / "adb"
    if not adb_dir.is_dir():
        adb_dir = cocbot / "adb"

    attacks_dir = cocbot / "attack"
    if not attacks_dir.is_dir():
        attacks_dir = src / "attack"

    return ProjectPaths(
        src_dir=src,
        cocbot_dir=cocbot,
        templates_dir=src / "Templates",
        models_dir=src / "models",
        datasets_dir=src / "datasets",
        walls_dir=src / "walls",
        profiles_dir=src / "profiles",
        images_dir=src / "images",
        debug_dir=src / "debug",
        logs_dir=src / "logs",
        adb_dir=adb_dir,
        adb_bin=adb_dir / "adb.exe",
        attacks_dir=attacks_dir,
        settings_json=src / "settings.json",
        army_presets_json=src / "army_presets.json",
        autohotkey_exe=src / "AutoHotkey" / "v2" / "AutoHotkey64.exe",
    )
