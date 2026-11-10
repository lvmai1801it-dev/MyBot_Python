# ==== COCbot/platform/ahk.py ====
import os
import sys
import subprocess
import time
from pathlib import Path

import COCbot.app.paths as paths

ahk_folder = Path(paths.AHK_DIR)
ahk_exe = Path(paths.AHK_EXE)


def run_ahk(script_name: str, wait: float = 2.0) -> bool:
    script_path = ahk_folder / script_name

    if not ahk_exe.is_file():
        print(f"[WARN] AutoHotkey binary not found at: {ahk_exe}. Skipping '{script_name}'.")
        return False
    if not script_path.is_file():
        print(f"[WARN] AHK script not found: '{script_path}'. Skipping.")
        return False

    try:
        subprocess.run(
            [str(ahk_exe), str(script_path)],
            cwd=str(ahk_folder),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            check=True,
        )
        time.sleep(wait)
        return True
    except Exception as e:
        print(f"[WARN] Failed to run AHK script '{script_name}': {e}")
        return False
