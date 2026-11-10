# ==== COCbot/app/config.py ====
import os
import subprocess
import sys

from COCbot.app import paths

BASE_DIR = str(paths.BASE_DIR)
ADB_BIN = str(paths.ADB_BIN)
ADB_DIR = str(paths.ADB_DIR)
ATTACKS_DIR = str(paths.ATTACKS_DIR)
AHK_EXE = str(paths.AHK_EXE)
TEMPLATE_DIR = str(paths.TEMPLATE_DIR)

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

NEXT_BTN_TEMPLATE = os.path.join(TEMPLATE_DIR, 'next_button.png')
END_BATTLE_TEMPLATE = os.path.join(TEMPLATE_DIR, 'end_battle.png')
TEMPLATE_FILES = ['disconnected.png']
THRESHOLD = 0.88

CLAN_CAPITAL_SCENERY_DIR = os.path.join(TEMPLATE_DIR, 'Clan Capital', 'Scenery')
CLAN_CAPITAL_DIR = os.path.join(TEMPLATE_DIR, 'Clan Capital')
CLAN_CAPITAL_THRESH = 0.65
CLAN_CAPITAL_CACHE = os.path.join(BASE_DIR, 'profiles', 'clan_capital_tpl.txt')

CC_THRESH_PCT = 75
CC_TPL_AVAILABLE_ATKS = 'available_attacks.png'
CC_TPL_ENEMY_LAND = 'capital_enemy.png'
CC_TPL_VILLAGE_3STAR = 'capital_3star.png'
CC_TPL_VILLAGE_AVAIL = 'capital_available.png'
CC_TPL_TROOPS_READY = 'capital_troops_ready.png'
CC_TPL_FULL_GOLD_WINDOW = 'capital_full_gold_window.png'
CC_DIR_SPELLS = os.path.join(CLAN_CAPITAL_DIR, 'Spells')
CC_DIR_TROOPS = os.path.join(CLAN_CAPITAL_DIR, 'Troops')
CP_FRESH_TEMPLATE = os.path.join(CLAN_CAPITAL_DIR, 'capital_cp_fresh.png')
CP_FRESH_THRESHOLD = 0.95

DROP_SPACING = 180
DROP_THRESH = 0.7
SURRENDER_THRESH = 0.88
MAX_VILLAGES = 5

NEXT_THRESH = 0.35
MAX_WAIT_BATTLE = 170

MEMU = '127.0.0.1:21503'
BLUESTACKS = '127.0.0.1:5556'
LDPLAYER = '127.0.0.1:5555'

CC_VILLAGE_ORDER = [
    'Goblin Mines', 'Skeleton Park', 'Golem Quarry',
    'Balloon Lagoon', "Builder's Workshop", 'Dragon Cliffs',
    'Wizard Valley', 'Barbarian Camp', 'Capital Peak',
]

CC_TROOP_TAP_COUNTS = {
    's_miner.png': 11,
    'mountain_golem.png': 2,
    's_dragon.png': 4,
    'pekka.png': 3,
    'flying_fortress.png': 2,
}

BATTLE_KEYWORDS = [
    'victory', 'defeat', 'you got:',
    'troops expended', 'return', 'home',
]

DEFAULT_CFG = {
    'gold_threshold': 65000,
    'elixir_threshold': 65000,
    'dark_elixir_threshold': 0,
    'upgrade_wall': True,
    'wall_level': 12,
    'wall_gold_threshold': 5000000,
    'wall_elixir_threshold': 5000000,
    'request_troops': True,
    'attack': 'Dragon_Attack',
    'train_mode': 'smart',
    'quick_slot': 1,
    'enable_clan_capital': False,
    'capital_hall_level': 7,
}
