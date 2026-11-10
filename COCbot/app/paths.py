# ==== COCbot/app/paths.py ====
"""
Central path resolution.

Only ``SRC_DIR`` is added to ``sys.path`` so that ``import COCbot.*`` works.
We deliberately do NOT add ``COCBOT_DIR`` (or its subpackages) to ``sys.path``:
doing so shadows stdlib modules such as ``platform`` and breaks third-party
libraries.
"""
import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    SRC_DIR = os.path.dirname(sys.executable)
else:
    _curr = os.path.abspath(os.path.dirname(__file__))
    _p = _curr
    _found_src = None
    for _ in range(6):
        if (os.path.isdir(os.path.join(_p, 'Templates')) or
                os.path.isfile(os.path.join(_p, 'settings.json')) or
                os.path.isdir(os.path.join(_p, 'COCbot'))):
            _found_src = _p
            break
        _parent = os.path.dirname(_p)
        if _parent == _p:
            break
        _p = _parent

    SRC_DIR = _found_src if _found_src else os.path.abspath(os.path.join(_curr, '..', '..'))

COCBOT_DIR = os.path.join(SRC_DIR, 'COCbot')
if not os.path.isdir(COCBOT_DIR):
    COCBOT_DIR = os.path.abspath(os.path.join(_curr, '..'))

# Make ``import COCbot.*`` work. Never add COCBOT_DIR itself: a package named
# ``platform`` inside it would shadow the standard-library module.
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

BASE_DIR = SRC_DIR
ROOT = SRC_DIR

TEMPLATE_DIR = os.path.join(SRC_DIR, 'Templates')
PROFILES_DIR = os.path.join(SRC_DIR, 'profiles')
WALLS_DIR = os.path.join(SRC_DIR, 'walls')
SETTINGS_JSON = os.path.join(SRC_DIR, 'settings.json')
ARMY_PRESETS_JSON = os.path.join(SRC_DIR, 'army_presets.json')

# ADB path: prefer the bundled copy under the project, then COCbot/adb.
ADB_DIR = os.path.join(SRC_DIR, 'adb')
if not os.path.isdir(ADB_DIR):
    ADB_DIR = os.path.join(COCBOT_DIR, 'adb')
ADB_BIN = os.path.join(ADB_DIR, 'adb.exe')

# Attack resources live in COCbot/attack.
ATTACKS_DIR = os.path.join(COCBOT_DIR, 'attack')
if not os.path.isdir(ATTACKS_DIR):
    ATTACKS_DIR = os.path.join(SRC_DIR, 'attack')

# AutoHotkey
AHK_DIR = os.path.join(SRC_DIR, 'AutoHotkey', 'v2')
if not os.path.isdir(AHK_DIR):
    AHK_DIR = os.path.join(COCBOT_DIR, 'AutoHotkey', 'v2')
AHK_EXE = os.path.join(AHK_DIR, 'AutoHotkey64.exe')

TEMPLATE_PATH = Path(TEMPLATE_DIR)
PROFILES_PATH = Path(PROFILES_DIR)
WALLS_PATH = Path(WALLS_DIR)
ATTACKS_PATH = Path(ATTACKS_DIR)
