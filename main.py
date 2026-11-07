# ==== main.py ====
import glob
import json
import os
import time

import cv2

import state
from state import pause_event, stop_event
from config import (
    BASE_DIR, ATTACKS_DIR, TEMPLATE_DIR, TEMPLATE_FILES, THRESHOLD,
    NEXT_BTN_TEMPLATE, END_BATTLE_TEMPLATE, MAX_VILLAGES,
    CLAN_CAPITAL_SCENERY_DIR, DEFAULT_CFG,
)
from core.coords import (
    RETURN_HOME_TAP, BATTLE_BUTTON_TAP, FIND_MATCH_TAP, ATTACK_CONFIRM_TAP,
    NEXT_SEARCH_TAP, MENU_TAP, RV_BACK_TAP, RV_CLOSE_SETTINGS_TAP,
)
from routines.clan_games import run_events_open
from routines.Tap_Collectors import find_and_tap_collectors
from routines.IsTarget import extract_resources
from routines.request_troops import auto_request
from routines.home_routine import handle_home_resources
from routines.boot_recovery import boot_recovery
from routines.ensure_home_base import ensure_home_base
from routines.smart_train import smart_train
from routines.quick_train import quick_train
from routines.ready_villages import prepare_accounts, switch_to_village
from routines.zoom_out import multi_zoom_out
from gui.wizard_bridge import bridge
from PyQt5.QtCore import QEventLoop
from attacks.attacks import run_attack as attack_dispatch

from emulator_setup import setup_emulator
from controls import _check_stop, pause_bot, resume_bot
from stats_manager import _stats_file_path, _load_stats_from_disk, zero_all_stats_files
from adb_utils import tap, return_home
from battle_helpers import (
    search_attack, search_next, connection_popup_visible,
    wait_for_scout_screen, battle_ended, wait_battle_end,
    is_next_button_present, treasure_event,
    get_stars_from_screen, gain_resources,
)
from stats_manager import _stats_file_path, _load_stats_from_disk
from clan_capital import clan_capital


ATTACK_FUNCS = {
    'Dragon_Attack': attack_dispatch,
    'ElectroDragon_Attack': attack_dispatch,
}

# Validate templates on import
for tpl in (NEXT_BTN_TEMPLATE, END_BATTLE_TEMPLATE):
    if not os.path.isfile(tpl):
        raise FileNotFoundError(f'❌ Template not found: {tpl}')


def one_cycle(cfg):
    pause_event.wait()
    if _check_stop():
        print('[INFO] Cycle aborted before home-prep')
        state._saved_wall_offset = None
        state.wall_save = False
        return

    treasure_event()
    pause_event.wait()
    ensure_home_base()
    tap(*MENU_TAP)

    if connection_popup_visible():
        print('[WARN] Connection lost → recovering')
        boot_recovery()
        return

    if _check_stop():
        print('[INFO] Cycle aborted before prep')
        state._saved_wall_offset = None
        state.wall_save = False
        return

    print('ZOOMING OUT . . .')
    pause_event.wait()
    multi_zoom_out(state.host)

    if cfg.get('enable_clan_capital', False) and not _check_stop():
        while True:
            pause_event.wait()
            started = clan_capital(cfg)
            if not started:
                print('[CC] No attacks available or CC not ready → exiting CC loop.')
                break
            time.sleep(1.0)
            print('[CC] Rebooting Clash for next CC pass…')
            boot_recovery()
            if _check_stop():
                break
            pause_event.wait()
            ensure_home_base()
            tap(*MENU_TAP)
            time.sleep(0.5)
            pause_event.wait()
            try:
                multi_zoom_out(state.host)
            except Exception as e:
                print(f'[CC] Zoom-out failed: {e}')
                break
            if connection_popup_visible():
                print('[CC] Connection lost → recovering')
                boot_recovery()
                break
            if _check_stop():
                break

    if connection_popup_visible():
        print('[WARN] Connection lost → recovering')
        boot_recovery()
        return

    if _check_stop():
        print('[INFO] Cycle aborted before collecting')
        state._saved_wall_offset = None
        state.wall_save = False
        return

    pause_event.wait()
    if cfg['train_mode'] == 'quick':
        print('[quick_train] using quick train to cook army.')
        if state._cycle_count % 5 == 0:
            pause_event.wait()
            quick_train(cfg['quick_slot'])
    else:
        if state._cycle_count % 3 == 0:
            pause_event.wait()
            smart_train(cfg)

    pause_event.wait()
    if connection_popup_visible():
        print('[WARN] Connection lost → recovering')
        boot_recovery()
        return

    if cfg['upgrade_wall'] and not _check_stop():
        print(f"[INFO] Upgrading walls to level {cfg['wall_level']} if thresholds met…")
        handle_home_resources(
            cfg['wall_level'],
            cfg['wall_gold_threshold'],
            cfg['wall_elixir_threshold'],
        )

    pause_event.wait()
    if cfg.get('enable_clan_games', False):
        print('[INFO] Running Clan Games…')
        run_events_open(state.host)
        if _check_stop():
            state._saved_wall_offset = None
            state.wall_save = False
            return

    pause_event.wait()
    time.sleep(0.5)

    if cfg['request_troops'] and not _check_stop():
        if connection_popup_visible():
            print('[WARN] Connection lost → recovering')
            boot_recovery()
            return
        print('[INFO] Requesting troops')
        auto_request()

    pause_event.wait()
    if _check_stop():
        print('[INFO] Cycle aborted before search')
        state._saved_wall_offset = None
        state.wall_save = False
        return

    if connection_popup_visible():
        print('[WARN] Connection lost → recovering')
        boot_recovery()
        return

    find_and_tap_collectors()

    print(f"[INFO] Search criteria -> Gold ≥ {cfg['gold_threshold']}, "
          f"Elixir ≥ {cfg['elixir_threshold']}")
    print('[INFO] Searching for base to attack...')
    pause_event.wait()
    search_attack()
    pause_event.wait()

    while not _check_stop():
        pause_event.wait()
        if connection_popup_visible():
            print('[WARN] Connection lost during evaluation → recovering')
            boot_recovery()
            return

        if not wait_for_scout_screen():
            print('[WARN] Scouting UI not detected → recovering')
            boot_recovery()
            return

        for attempt in range(1, 4):
            pause_event.wait()
            if is_next_button_present():
                break
            print(f'⚠️ Next button missing—retrying ({attempt}/3)')
            time.sleep(2)
        else:
            print('⚠️ Next button still missing after 3 attempts—triggering recovery')
            boot_recovery()
            print('✅ Recovered successfully')
            break

        pause_event.wait()
        e_gold, e_elixir, e_dark_elixir = map(int, extract_resources())
        print(f'[LOOT] GOLD: {e_gold}  ELIXIR: {e_elixir}  DARK_ELIXIR: {e_dark_elixir}')
        pause_event.wait()

        if (e_gold >= cfg['gold_threshold']
                and e_elixir >= cfg['elixir_threshold']
                and e_dark_elixir >= cfg['dark_elixir_threshold']):
            print('[INFO] Good base found → attacking')
            attack_fn = ATTACK_FUNCS.get(cfg['attack'])
            if not attack_fn:
                print(f"[ERROR] Unknown attack: {cfg['attack']!r}")
                return

            pause_event.wait()
            attack_fn(cfg)
            pause_event.wait()
            wait_battle_end()

            if cfg.get('enable_stats', False):
                village_idx = cfg['current_village_idx']
                try:
                    stars_got = get_stars_from_screen()
                except Exception:
                    stars_got = 0

                e_gold, e_elixir, e_dark_elixir = gain_resources(stars_got)

                stats = _load_stats_from_disk(village_idx)
                stats['gold'] = stats.get('gold', 0) + e_gold
                stats['elixir'] = stats.get('elixir', 0) + e_elixir
                stats['de'] = stats.get('de', 0) + e_dark_elixir
                stats['attacks'] = stats.get('attacks', 0) + 1

                key = str(stars_got)
                stars_block = stats.setdefault('stars', {'0': 0, '1': 0, '2': 0, '3': 0})
                stars_block[key] = stars_block.get(key, 0) + 1
                stats['stars'] = stars_block
                stats['last_update_ts'] = time.time()

                with open(_stats_file_path(village_idx), 'w') as f:
                    json.dump(stats, f, indent=2)
                cfg['stats'] = stats
            else:
                print(f'[{time.strftime("%H:%M:%S")}] '
                      '[WORKER] ENABLE_STATS=False, skipping stats update')

            return_home()
            break
        else:
            print('[INFO] Loot below threshold → next')
            search_next()

    pause_event.wait()
    if connection_popup_visible():
        print('Connection lost detected—recovering…')
        boot_recovery()
        return

    time.sleep(2)
    state._cycle_count += 1


def bot_loop(cfg):
    # --- ĐỒNG BỘ CẤU HÌNH TỪ GUI (main.host) SANG STATE ---
    if globals().get('host'):
        state.host = globals()['host']
    if globals().get('emulator_key'):
        state.emulator_key = globals()['emulator_key']
    if globals().get('ld_index') is not None:
        state.ld_index = globals()['ld_index']
    if globals().get('ld_name'):
        state.ld_name = globals()['ld_name']
    # ------------------------------------------------------

    setup_emulator()
    pause_event.wait()

    ensure_home_base()
    tap(*MENU_TAP)
    time.sleep(2)
    pause_event.wait()

    if connection_popup_visible():
        print('Connection lost detected—recovering…')
        boot_recovery()
        ensure_home_base()
        tap(*MENU_TAP)
        time.sleep(2)

    profiles_dir = os.path.join(BASE_DIR, 'profiles')
    json_paths = glob.glob(os.path.join(profiles_dir, 'Village_*.json'))
    existing_count = len(json_paths)
    desired_count = min(len(cfg['selected_villages']), 5)
    selected = cfg.get('selected_villages', [])

    if cfg['enable_multi_account']:
        pause_event.wait()
        if stop_event.is_set(): return

        if existing_count == 0:
            print(f'[INFO] No existing village profiles → configuring {selected}')
            bridge.requestWizard.emit(selected)
            loop = QEventLoop()
            bridge.wizardDone.connect(loop.quit)
            loop.exec_()
            bridge.wizardDone.disconnect(loop.quit)
        elif desired_count > existing_count:
            print(f'[INFO] {existing_count} profiles found, need {desired_count} '
                  f'→ configuring villages {existing_count + 1}–{desired_count}')
            bridge.requestWizard.emit(cfg['selected_villages'])
            loop = QEventLoop()
            bridge.wizardDone.connect(loop.quit)
            loop.exec_()
            bridge.wizardDone.disconnect(loop.quit)
            time.sleep(1)
            boot_recovery()
            ensure_home_base()
            tap(*MENU_TAP)
        else:
            print(f'[INFO] {existing_count} profiles match desired {desired_count}, no prep needed')
            time.sleep(1)
            prepare_accounts(start=1, count=None)
            print('Cleaning. . .')
            time.sleep(6)
            tap(*RV_BACK_TAP)
            time.sleep(1)
            tap(*RV_CLOSE_SETTINGS_TAP)
            time.sleep(1)
    else:
        print('[INFO] Multi-village disabled → single-village mode')

    pause_event.wait()
    if stop_event.is_set(): return

    accounts_file = os.path.join(profiles_dir, 'accounts.txt')
    accounts_count = 1
    if os.path.isfile(accounts_file):
        try:
            accounts_count = int(open(accounts_file).read().strip())
        except ValueError:
            print('Value Error')
    else:
        print('accounts.txt does not exist.')

    if cfg['enable_multi_account'] and accounts_count == 1:
        print('[WARN] We found 1 account only. Forcing Single Mode Village.')
        cfg['enable_multi_account'] = False

    pause_event.wait()
    if stop_event.is_set(): return

    if cfg['enable_multi_account']:
        user_list = cfg['selected_villages']
        if len(user_list) > accounts_count:
            print(f'[WARN] You requested {len(user_list)} villages but only '
                  f'{accounts_count} exist → using first {accounts_count}.')
            cfg['selected_villages'] = user_list[:accounts_count]

    # SINGLE
    if not cfg['enable_multi_account']:
        state._cycle_count = 0
        cfg['current_village_idx'] = 1
        while not stop_event.is_set():
            pause_event.wait()
            if stop_event.is_set(): break
            one_cycle(cfg)
        print('[INFO] Bot stopped')
        state._saved_wall_offset = None
        state.wall_save = False
        return

    # MULTI
    village_list = cfg['selected_villages']
    interval_secs = cfg['multi_interval_mins'] * 60
    mins = interval_secs / 60.0
    time_str = f'{mins/60:.1f} hr' if mins >= 60 else f'{mins:.1f} minutes'
    print(f'[INFO] Cycling through villages {village_list} every {time_str}')
    pause_event.wait()

    while not stop_event.is_set():
        for idx in village_list:
            if stop_event.is_set(): break

            pause_event.wait()
            if connection_popup_visible():
                print('Connection lost detected—recovering…')
                boot_recovery()
                break

            state._cycle_count = 0

            if existing_count == 0:
                print(f'[INFO] First setup: cleaning & ensuring home for Village_{idx}')
                boot_recovery()
                pause_event.wait()
                ensure_home_base()
                pause_event.wait()
                tap(*MENU_TAP)
                time.sleep(3)
                existing_count = accounts_count

            pause_event.wait()
            if stop_event.is_set(): break

            ensure_home_base()
            tap(*MENU_TAP)
            print(f'[INFO] → Switching to Village_{idx}')
            bridge.setActiveVillage.emit(idx)
            switch_to_village(idx)
            time.sleep(5)

            pause_event.wait()
            if stop_event.is_set(): break

            ensure_home_base()
            tap(*MENU_TAP)
            state._saved_wall_offset = None
            state.wall_save = False
            cfg['current_village_idx'] = idx

            cfg_path = os.path.join(profiles_dir, f'Village_{idx}.json')
            village_cfg = {}
            try:
                with open(cfg_path, 'r') as f:
                    village_cfg = json.load(f)
            except FileNotFoundError:
                print(f'[WARN] Missing config for Village_{idx}, using defaults')

            for k in ('enable_trophy_drop', 'trophy_limit', 'target_trophy'):
                village_cfg.pop(k, None)
            village_cfg.setdefault('enable_clan_capital', False)
            village_cfg.setdefault('capital_hall_level', 9)

            merged_cfg = {}
            merged_cfg.update(cfg)
            merged_cfg.update(village_cfg)

            slot_start = time.time()
            while time.time() - slot_start < interval_secs:
                pause_event.wait()
                if stop_event.is_set():
                    state._saved_wall_offset = None
                    state.wall_save = False
                    break
                one_cycle(merged_cfg)

    print('[INFO] Bot stopped')
    state._saved_wall_offset = None
    state.wall_save = False


def main(config=None):
    try:
        bot_loop(config)
    except KeyboardInterrupt:
        stop_event.set()
        print('\n[MAIN] Interrupted by user, exiting...')


if __name__ == '__main__':
    default_config = dict(
        DEFAULT_CFG,
        selected_villages=[1],
        current_village_idx=1,
        multi_interval_mins=60,
        enable_stats=False,
    )
    main(default_config)