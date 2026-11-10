# ==== COCbot/gui/constants.py ====
"""Shared GUI paths and emulator host constants."""
import COCbot.app.paths

BASE_DIR = str(COCbot.app.paths.SRC_DIR)
APP_DIR = BASE_DIR
ATTACK_DIR = str(COCbot.app.paths.ATTACKS_DIR)
BG = str(COCbot.app.paths.TEMPLATE_DIR)
TEMPLATES_DIR = BG
CFG_PATH = str(COCbot.app.paths.SETTINGS_JSON)
profiles_dir = str(COCbot.app.paths.PROFILES_DIR)

MEMU = "127.0.0.1:21503"
BLUESTACKS = "127.0.0.1:5556"
LDPLAYER = "127.0.0.1:5555"
