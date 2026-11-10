# ==== COCbot/game/battle/ensure_home_base.py ====
import time

import COCbot.app.paths  # noqa: F401
from COCbot.app import state
from COCbot.game.account.boot_recovery import boot_recovery
from COCbot.game.battle.detect_home_base import detect_home_base


def ensure_home_base(max_wait=50):
    print("🧠 Checking if we're on the home base screen...")
    # If a Shop/Army/Settings panel is covering the village, close it first;
    # otherwise detect_home_base() fails and we restart the whole game.
    try:
        from COCbot.game.village.ui_state import close_open_panels
        close_open_panels()
    except Exception as e:
        print(f'[UI] panel check skipped: {e}')

    start_time = time.time()

    while time.time() - start_time < max_wait:
        if state.stop_event.is_set():
            print('[STOP] home-base wait aborted')
            return False
        if detect_home_base():
            print('✅ Home base confirmed.')
            return True
        print('⏳ Still not on home base. Retrying in 5s...')
        time.sleep(5)

    print('❌ Failed to detect home base. Initiating reboot sequence...')
    boot_recovery()
    return ensure_home_base(max_wait=20)


if __name__ == '__main__':
    ensure_home_base()
