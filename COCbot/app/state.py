# ==== COCbot/app/state.py ====
import threading

# ADB target
host = None
ld_index = 0
ld_name = None
emulator_key = None

# Flow control
stop_event = threading.Event()
pause_event = threading.Event()
pause_event.set()

# Cycle counter / vestigial
_cycle_count = 0
_saved_wall_offset = None
wall_save = False
# Per-account attack counters: {account_key: attacks_done}
_switch_attack_counts = {}
# Last resources read from the Home Village
current_resources = {}
# Optional callable(dict) invoked after the home village is zoomed out, so the
# shell can refresh its resource readout from the same screen.
resource_hook = None
# Optional callable() that runs the ticked upgrades at the start of a cycle.
upgrade_hook = None
