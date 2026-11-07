# ==== ahk_utils.py ====
import sys
import subprocess
import time
from pathlib import Path

import core.paths

ahk_folder = Path(core.paths.AHK_DIR)
ahk_exe = Path(core.paths.AHK_EXE)


def run_ahk(script_name: str, wait: float = 2.0):
    script_path = ahk_folder / script_name

    if not ahk_exe.is_file():
        raise FileNotFoundError(f'Couldn’t find AHK binary: {ahk_exe}')
    if not script_path.is_file():
        raise FileNotFoundError(f'Couldn’t find script: {script_path}')

    subprocess.run(
        [str(ahk_exe), str(script_path)],
        cwd=str(ahk_folder),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=True,
    )

    time.sleep(wait)
