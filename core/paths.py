# ==== src/core/paths.py ====
import os
import sys

if getattr(sys, 'frozen', False):
    SRC_DIR = os.path.dirname(sys.executable)
else:
    SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Ensure SRC_DIR is first in sys.path
if SRC_DIR in sys.path:
    sys.path.remove(SRC_DIR)
sys.path.insert(0, SRC_DIR)

# Auto-add subpackages to sys.path (excluding attacks to avoid shadowing package attacks)
for subdir in ['core', 'gui', 'routines', 'emulators', 'utils']:
    p = os.path.abspath(os.path.join(SRC_DIR, subdir))
    if p not in sys.path:
        sys.path.append(p)

from pathlib import Path

BASE_DIR = SRC_DIR
ROOT = SRC_DIR

TEMPLATE_DIR = os.path.join(SRC_DIR, 'Templates')
PROFILES_DIR = os.path.join(SRC_DIR, 'profiles')
WALLS_DIR = os.path.join(SRC_DIR, 'walls')
ATTACKS_DIR = os.path.join(SRC_DIR, 'attacks')
SETTINGS_JSON = os.path.join(SRC_DIR, 'settings.json')
ADB_DIR = os.path.join(SRC_DIR, 'adb')
ADB_BIN = os.path.join(ADB_DIR, 'adb.exe')
AHK_DIR = os.path.join(SRC_DIR, 'AutoHotkey', 'v2')
AHK_EXE = os.path.join(AHK_DIR, 'AutoHotkey64.exe')

TEMPLATE_PATH = Path(TEMPLATE_DIR)
PROFILES_PATH = Path(PROFILES_DIR)
ATTACKS_PATH = Path(ATTACKS_DIR)
