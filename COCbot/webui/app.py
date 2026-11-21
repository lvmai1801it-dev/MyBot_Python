"""pywebview shell: a web front-end for the proven bot runtime.

Replaces neither the Qt GUI nor its workflow - it runs beside it
(``python run_web.py``) and drives the exact same backend seams:

    settings_store.load_settings/save_settings   (same settings.json)
    bootstrap.bot_loop(cfg)                      (worker thread)
    state.stop_event / pause_event               (start/stop/pause)
    app.upgrade_hook.install/uninstall           (auto-upgrade per cycle)
    app.emulator_detect.detect_memu              (auto-pick MEmu)

The JS side (``webui/index.html``) polls get_logs/get_state for live
updates, so no Qt signal plumbing is needed anywhere.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections import deque

import webview

from COCbot.app import emulator_detect, state as main
from COCbot.gui.settings_store import load_settings, save_settings

# Keys the web form does not own; always preserved from settings.json so
# a web-side save can never silently drop the Qt-side or runtime fields.
_PRESERVED_KEYS = (
    "redline_model", "deploy_zone_model", "redline_offset_ratio",
    "auto_capture_dataset", "auto_capture_dir",
    "auto_capture_min_interval_sec", "auto_capture_max_files",
    "auto_capture_only_on_fallback", "auto_capture_success_sample",
    "auto_capture_scout_sample", "auto_capture_on_scout",
    "auto_capture_on_attack", "auto_capture_format",
    "auto_capture_jpeg_quality", "auto_capture_webp_quality",
    "auto_capture_png_compression",
    "recipe_name", "recipe", "attack_sides",
    "log_level", "log_file_enabled", "log_file_path",
    "log_max_bytes", "log_backup_count",
    "emulator_type", "emulator_host", "ld_index",
    "hero_priorities", "defense_priorities", "army_priorities",
    "resource_priorities", "other_buildings", "buildings_priorities",
    "equipment_priorities", "pets_priorities",
)


class _Ring:
    """Thread-safe bounded log buffer fed by a stdout redirector."""

    def __init__(self, capacity: int = 3000) -> None:
        self.lines: deque[str] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def write(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            for line in text.splitlines():
                if line.strip():
                    self.lines.append(line)

    def flush(self) -> None:
        return None

    def tail(self, after: int = 0) -> tuple[list[str], int]:
        """Return (new lines since *after*, latest index)."""
        with self._lock:
            snapshot = list(self.lines)
        if after >= len(snapshot):
            return [], after
        return snapshot[after:], len(snapshot)


class BotApi:
    """Bridge exposed to JavaScript as ``pywebview.api.*``."""

    def __init__(self) -> None:
        self._worker: threading.Thread | None = None
        self._ring = _Ring()
        self._saved_stdout = None
        self._saved_stderr = None
        self._lock_socket: socket.socket | None = None
        self._paused = False

    # ---------------------------------------------------------------- state
    def get_state(self) -> dict:
        """Live bot state for the status bar."""
        return {
            "running": self._worker is not None and self._worker.is_alive(),
            "paused": self._paused,
            "host": getattr(main, "host", None),
            "stopped": main.stop_event.is_set(),
        }

    def get_settings(self) -> dict:
        """Current settings.json contents (defaults when missing)."""
        return load_settings()

    def save_settings(self, form: dict | None = None) -> dict:
        """Merge *form* over the stored settings and persist them."""
        cfg = load_settings()
        for key, value in (form or {}).items():
            cfg[key] = value
        save_settings(cfg)
        return {"ok": True, "settings": cfg}

    # ----------------------------------------------------------------- logs
    def get_logs(self, after: int = 0) -> dict:
        """Poll endpoint: log lines appended since index *after*."""
        lines, index = self._ring.tail(int(after or 0))
        return {"lines": lines, "index": index}

    # ----------------------------------------------------------------- bot
    def start(self, form: dict | None = None) -> dict:
        """Start the bot worker: auto-detect MEmu, merge settings, run."""
        if self._worker is not None and self._worker.is_alive():
            return {"ok": False, "error": "Bot is already running"}

        detected, reason = emulator_detect.detect_memu()
        if not detected:
            return {"ok": False, "error": "Khong tim thay MEmu (online/installed)"}
        main.emulator_key = "memu"
        main.ld_index = 0
        main.ld_name = None
        main.host = emulator_detect.MEMU_HOST

        # Single-instance lock, mirroring the Qt GUI's port bind.
        if self._lock_socket is not None:
            try:
                self._lock_socket.close()
            except OSError:
                pass
            self._lock_socket = None
        lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            lock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            lock.bind(("127.0.0.1", 6200))
        except OSError:
            return {"ok": False, "error": "Mot bot khac dang giu MEmu (port 6200)"}
        self._lock_socket = lock

        cfg = self._collect_cfg(form)
        save_settings(cfg)

        main.stop_event.clear()
        main.pause_event.set()
        self._paused = False

        from COCbot.app import upgrade_hook

        upgrade_hook.install()

        from COCbot.app.bootstrap import bot_loop

        self._capture_stdout()
        self._worker = threading.Thread(target=bot_loop, args=(cfg,), daemon=True)
        self._worker.start()
        print(f"[WEB] Bot khoi dong: {reason} @ {main.host}")
        return {"ok": True, "reason": reason}

    def stop(self) -> dict:
        """Cooperative stop; the worker exits at its next checkpoint."""
        main.stop_event.set()
        main.pause_event.set()
        from COCbot.app import upgrade_hook

        upgrade_hook.uninstall()
        print("[WEB] Dang dung bot...")
        return {"ok": True}

    def pause(self) -> dict:
        main.pause_event.clear()
        self._paused = True
        print("[WEB] Pause - bot dung o diem an toan ke tiep")
        return {"ok": True}

    def resume(self) -> dict:
        main.pause_event.set()
        self._paused = False
        print("[WEB] Resume")
        return {"ok": True}

    # -------------------------------------------------------------- helpers
    def _collect_cfg(self, form: dict | None) -> dict:
        """Stored settings + web form overrides + preserved runtime keys."""
        cfg = load_settings()
        for key, value in (form or {}).items():
            cfg[key] = value
        stored = load_settings()
        for key in _PRESERVED_KEYS:
            if key in stored and key not in cfg:
                cfg[key] = stored[key]
        cfg["stats"] = {}
        return cfg

    def _capture_stdout(self) -> None:
        """Route worker prints into the ring (once, restored on close)."""
        import sys

        if self._saved_stdout is None:
            self._saved_stdout = sys.stdout
            self._saved_stderr = sys.stderr
            sys.stdout = self._ring
            sys.stderr = self._ring


def run() -> None:
    """Open the 480x670 frameless web window.

    (Named ``run`` because ``main`` is bound to ``COCbot.app.state`` -
    the same convention as gui/app.py.)

    Environment (loaded from ``COCbot/webui/.env`` if present; a real
    environment variable always wins over the file):

    - ``WEBUI_DEV_URL`` - load the Vite dev server instead of a build
      (hot reload while coding the UI).
    - ``WEBUI_WIDTH`` / ``WEBUI_HEIGHT`` - window size (default 480x670).

    Resolution order for the page:
    1. ``WEBUI_DEV_URL``
    2. ``frontend/dist/index.html`` - the built React app
       (``npm run build`` inside COCbot/webui/frontend).
    3. ``webui/index.html`` - the zero-dependency fallback page.
    """
    import os
    from pathlib import Path

    # Optional .env workflow file next to this module.
    env_file = Path(__file__).with_name(".env")
    if env_file.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file, override=False)
        except ImportError:
            pass

    api = BotApi()
    dev_url = os.environ.get("WEBUI_DEV_URL")
    react_index = Path(__file__).parent / "frontend" / "dist" / "index.html"
    fallback = Path(__file__).with_name("index.html")
    if dev_url:
        url = dev_url
        print(f"[WEB] dev server: {dev_url}")
    elif react_index.is_file():
        url = str(react_index)
    else:
        url = str(fallback)
    try:
        width = int(os.environ.get("WEBUI_WIDTH", "480"))
        height = int(os.environ.get("WEBUI_HEIGHT", "860"))
    except ValueError:
        width, height = 480, 860
    webview.create_window(
        "MRB VM BOT MOD",
        url=url,
        js_api=api,
        width=width,
        height=height,
        min_size=(width, height),
        frameless=True,
        easy_drag=True,
    )
    webview.start()


if __name__ == "__main__":
    run()
