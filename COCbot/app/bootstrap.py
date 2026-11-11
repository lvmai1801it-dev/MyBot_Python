# ==== COCbot/app/bootstrap.py ====
import json
import os
import time

import COCbot.app.paths  # noqa: F401
from COCbot.app import state
from COCbot.app.config import (
    DEFAULT_CFG,
    END_BATTLE_TEMPLATE,
    NEXT_BTN_TEMPLATE,
)
from COCbot.app.controls import _check_stop
from COCbot.app.coords import (
    MENU_TAP,
)
from COCbot.app.stats import _load_stats_from_disk, _stats_file_path
from COCbot.attack.api import run_attack as attack_dispatch
from COCbot.emulator.setup import setup_emulator
from COCbot.game.account.boot_recovery import boot_recovery
from COCbot.game.account.shared_prefs import SharedPrefsManager
from COCbot.game.account.switch_config import (
    enabled_profiles,
    load_switch_config,
    save_switch_config,
)
from COCbot.game.battle.ensure_home_base import ensure_home_base
from COCbot.game.battle.helpers import (
    connection_popup_visible,
    gain_resources,
    get_stars_from_screen,
    is_next_button_present,
    search_attack,
    search_next,
    treasure_event,
    wait_battle_end,
    wait_for_scout_screen,
)
from COCbot.game.battle.target import extract_resources
from COCbot.game.clan.capital import clan_capital
from COCbot.game.clan.games import run_events_open
from COCbot.game.clan.requests import auto_request
from COCbot.game.training.quick_train import quick_train
from COCbot.game.training.smart_train import smart_train
from COCbot.game.village.collectors import find_and_tap_collectors
from COCbot.game.village.home_routine import handle_home_resources
from COCbot.game.village.ui_state import close_open_panels
from COCbot.game.village.zoom import multi_zoom_out
from COCbot.platform.adb_utils import return_home, tap
from COCbot.vision.redline.dataset_capture import get_capture

# Module-level emulator state & events
host = None
emulator_key = None
ld_index = None
ld_name = None
stop_event = state.stop_event
pause_event = state.pause_event

ATTACK_FUNCS = {
    'Dragon_Attack': attack_dispatch,
    'ElectroDragon_Attack': attack_dispatch,
}

# Validate templates on import
for tpl in (NEXT_BTN_TEMPLATE, END_BATTLE_TEMPLATE):
    if not os.path.isfile(tpl):
        raise FileNotFoundError(f'❌ Template not found: {tpl}')


def sync_state():
    global host, emulator_key, ld_index, ld_name
    if host is not None:
        state.host = host
    elif state.host is not None:
        host = state.host

    if emulator_key is not None:
        state.emulator_key = emulator_key
    elif state.emulator_key is not None:
        emulator_key = state.emulator_key

    if ld_index is not None:
        state.ld_index = ld_index
    elif state.ld_index is not None:
        ld_index = state.ld_index

    if ld_name is not None:
        state.ld_name = ld_name
    elif state.ld_name is not None:
        ld_name = state.ld_name


def _account_key_and_quota(conf, fallback_need):
    """Return (key, quota) for the currently active shared_prefs profile.

    Quota is the per-account `attacks` value; 0 means "use the shared
    consecutive_attacks setting".
    """
    current = str(conf.get("current_profile", "")).strip()
    entry = next(
        (a for a in conf.get("accounts", [])
         if a.get("enabled") and a.get("profile") == current),
        {},
    )
    quota = int(entry.get("attacks", 0) or 0) or fallback_need
    return f"profile:{current}", quota


def _reset_attack_count(key):
    counts = getattr(state, "_switch_attack_counts", None) or {}
    counts[key] = 0
    state._switch_attack_counts = counts


def _switch_to_next_account(conf, attacks_due=False, time_due=False):
    """Switch to the next enabled shared_prefs profile."""
    now = time.time()
    current = str(conf.get("current_profile", "")).strip()
    names = enabled_profiles(conf)
    if not current or len(names) < 2:
        return False

    try:
        idx = names.index(current)
    except ValueError:
        idx = -1
    target = names[(idx + 1) % len(names)]
    if target == current:
        return False

    print(f"[SWITCH] {current} -> {target} "
          f"(attacks={attacks_due}, time={time_due})")
    try:
        SharedPrefsManager().switch_profile(current, target)
    except Exception as e:
        print(f"[SWITCH] failed: {e}")
        return False

    conf["current_profile"] = target
    conf["last_switch_ts"] = now
    save_switch_config(conf)
    _reset_attack_count(f"profile:{current}")
    return True


def _maybe_switch_account(cfg, attack=True):
    """Auto-switch by attacks and/or time schedule."""
    conf = load_switch_config()
    if not conf.get("enabled"):
        return False

    by_attacks = bool(conf.get("use_attack_limit", True))
    by_time = bool(conf.get("use_time_schedule", False))
    if not by_attacks and not by_time:
        return False

    need = int(conf.get("consecutive_attacks", 2) or 2)

    now = time.time()
    time_due = False
    if by_time:
        last = float(conf.get("last_switch_ts", 0) or 0)
        if last <= 0:
            conf["last_switch_ts"] = now
            save_switch_config(conf)
        else:
            interval = max(1, int(conf.get("schedule_minutes", 60) or 60)) * 60
            time_due = (now - last) >= interval

    attacks_due = False
    if attack and by_attacks:
        key, quota = _account_key_and_quota(conf, need)
        counts = getattr(state, "_switch_attack_counts", None) or {}
        counts[key] = counts.get(key, 0) + 1
        state._switch_attack_counts = counts
        attacks_due = counts[key] >= quota
        print(f"[SWITCH] {key}: trận {counts[key]}/{quota}")

    if not (attacks_due or time_due):
        return False
    return _switch_to_next_account(conf, attacks_due, time_due)


def _wait_with_stop(seconds):
    """Sleep but remain responsive to Stop/Pause."""
    end = time.time() + max(0, seconds)
    while time.time() < end:
        if state.stop_event.is_set():
            return
        state.pause_event.wait()
        if state.stop_event.is_set():
            return
        time.sleep(min(2.0, max(0.0, end - time.time())))


def _maybe_switch_full_storages(cfg):
    """Switch when gold/elixir/DE are all full; if no other account, wait."""
    conf = load_switch_config()
    if not conf.get("enabled") or not conf.get("use_storage_full"):
        return False

    from COCbot.game.village.storage_full import detect_full_storages

    wait_min = max(1, int(conf.get("storage_full_wait_minutes", 10) or 10))
    threshold = float(conf.get("storage_full_threshold", 0.85) or 0.85)
    min_matches = int(conf.get("storage_full_min_matches", 1) or 1)
    warned_wait = False

    while not state.stop_event.is_set():
        state.pause_event.wait()
        if state.stop_event.is_set():
            return False

        status = detect_full_storages(
            threshold=threshold, min_matches=min_matches)
        if not status.get("all_full"):
            return False

        full_names = ", ".join(
            n for n in ("gold", "elixir", "de") if status[n]["full"])
        print(f"[SWITCH] Đầy 3 kho ({full_names}) → chuyển account.")

        conf = load_switch_config()  # GUI may have changed while idling
        if _switch_to_next_account(conf):
            print("[SWITCH] Đã chuyển account do đầy kho.")
            return True

        if not warned_wait:
            print(f"[SWITCH] Không có account khác để chuyển → "
                  f"treo {wait_min} phút rồi kiểm tra lại.")
            warned_wait = True
        _wait_with_stop(wait_min * 60)

    return False

def _notify_resources(resources=None):
    """Call the optional resource hook installed by the shell."""
    hook = getattr(state, 'resource_hook', None)
    if hook is None:
        return
    try:
        hook(resources or {})
    except Exception as e:
        print(f'[RES] resource readout skipped: {e}')


def _notify_upgrades():
    """Call the optional upgrade hook installed by the shell."""
    hook = getattr(state, 'upgrade_hook', None)
    if hook is None:
        return
    try:
        hook()
    except Exception as e:
        print(f'[UPGRADE] skipped: {e}')


def one_cycle(cfg):
    sync_state()
    try:
        close_open_panels()
    except Exception as e:
        print(f'[UI] panel check skipped: {e}')
    state.pause_event.wait()
    if _check_stop():
        print('[INFO] Cycle aborted before home-prep')
        state._saved_wall_offset = None
        state.wall_save = False
        return

    try:
        if _maybe_switch_account(cfg, attack=False):
            print('[SWITCH] Time schedule -> account switched')
            return
    except Exception as e:
        print(f'[SWITCH] time schedule skipped: {e}')

    treasure_event()
    state.pause_event.wait()
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
    state.pause_event.wait()
    multi_zoom_out(state.host)
    if not _check_stop():
        try:
            from COCbot.game.village.main_village import read_current_resources
            _notify_resources(read_current_resources())
        except Exception as e:
            print(f'[RES] resource readout skipped: {e}')

    try:
        if _maybe_switch_full_storages(cfg):
            print('[SWITCH] Full storage -> account switched')
            return
    except Exception as e:
        print(f'[SWITCH] storage check skipped: {e}')

    if cfg.get('enable_clan_capital', False) and not _check_stop():
        while True:
            state.pause_event.wait()
            started = clan_capital(cfg)
            if not started:
                print('[CC] No attacks available or CC not ready → exiting CC loop.')
                break
            time.sleep(1.0)
            print('[CC] Rebooting Clash for next CC pass…')
            boot_recovery()
            if _check_stop():
                break
            state.pause_event.wait()
            ensure_home_base()
            tap(*MENU_TAP)
            time.sleep(0.5)
            state.pause_event.wait()
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

    state.pause_event.wait()
    if not cfg.get('check_troops', False):
        print('[INFO] Check quân đang tắt -> bỏ qua kiểm tra/train quân')
    elif cfg['train_mode'] == 'quick':
        print('[quick_train] using quick train to cook army.')
        if state._cycle_count % 5 == 0:
            state.pause_event.wait()
            quick_train(cfg['quick_slot'])
    else:
        if state._cycle_count % 3 == 0:
            state.pause_event.wait()
            smart_train(cfg)

    state.pause_event.wait()
    if connection_popup_visible():
        print('[WARN] Connection lost → recovering')
        boot_recovery()
        return

    # Buildings/army/pets upgrades run before walls so loot goes into permanent
    # upgrades first; walls only use the builder this step leaves free.
    if not _check_stop():
        _notify_upgrades()

    if (
        cfg['upgrade_wall']
        and not _check_stop()
        and getattr(state, 'upgrade_hook', None) is None
    ):
        print(f"[INFO] Upgrading walls to level {cfg['wall_level']} if thresholds met…")
        handle_home_resources(
            cfg['wall_level'],
            cfg['wall_gold_threshold'],
            cfg['wall_elixir_threshold'],
        )

    state.pause_event.wait()
    if cfg.get('enable_clan_games', False):
        print('[INFO] Running Clan Games…')
        run_events_open(state.host)
        if _check_stop():
            state._saved_wall_offset = None
            state.wall_save = False
            return

    state.pause_event.wait()
    time.sleep(0.5)

    if cfg['request_troops'] and not _check_stop():
        if connection_popup_visible():
            print('[WARN] Connection lost → recovering')
            boot_recovery()
            return
        print('[INFO] Requesting troops')
        auto_request()

    state.pause_event.wait()
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
    state.pause_event.wait()
    search_attack()
    state.pause_event.wait()

    while not _check_stop():
        state.pause_event.wait()
        if connection_popup_visible():
            print('[WARN] Connection lost during evaluation → recovering')
            boot_recovery()
            return

        if not wait_for_scout_screen():
            print('[WARN] Scouting UI not detected → recovering')
            boot_recovery()
            return

        for attempt in range(1, 4):
            state.pause_event.wait()
            if is_next_button_present():
                break
            print(f'⚠️ Next button missing—retrying ({attempt}/3)')
            time.sleep(2)
        else:
            print('⚠️ Next button still missing after 3 attempts—triggering recovery')
            boot_recovery()
            print('✅ Recovered successfully')
            break

        state.pause_event.wait()
        e_gold_raw, e_elixir_raw, e_dark_raw, scout_img = extract_resources(return_image=True)
        e_gold, e_elixir, e_dark_elixir = int(e_gold_raw), int(e_elixir_raw), int(e_dark_raw)
        print(f'[LOOT] GOLD: {e_gold}  ELIXIR: {e_elixir}  DARK_ELIXIR: {e_dark_elixir}')

        good_base = (
            e_gold >= cfg['gold_threshold']
            and e_elixir >= cfg['elixir_threshold']
            and e_dark_elixir >= cfg['dark_elixir_threshold']
        )

        # Scout frames are the best redline dataset source: the base is fully
        # visible and there are no attack effects. Capture both good and
        # skipped bases, rate-limited/deduplicated inside DatasetCapture.
        if scout_img is not None:
            try:
                get_capture(cfg).maybe_capture(
                    scout_img,
                    tag="scout_good" if good_base else "scout_skip",
                    source="scout",
                    meta={
                        "gold": e_gold,
                        "elixir": e_elixir,
                        "dark_elixir": e_dark_elixir,
                        "thresholds": {
                            "gold": cfg['gold_threshold'],
                            "elixir": cfg['elixir_threshold'],
                            "dark_elixir": cfg['dark_elixir_threshold'],
                        },
                        "good_base": good_base,
                        "village_idx": 1,
                        "attack": cfg.get('attack'),
                    },
                )
            except Exception as e:
                print(f"[CAPTURE] scout skipped: {e}")

        state.pause_event.wait()

        if good_base:
            print('[INFO] Good base found → attacking')
            attack_fn = ATTACK_FUNCS.get(cfg['attack'])
            if not attack_fn:
                print(f"[ERROR] Unknown attack: {cfg['attack']!r}")
                return

            state.pause_event.wait()
            attack_fn(cfg)
            state.pause_event.wait()
            wait_battle_end()

            if cfg.get('enable_stats', False):
                village_idx = 1
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

            if _maybe_switch_account(cfg):
                print('[SWITCH] Account switched; restarting cycle')
                return

            return_home()
            break
        else:
            print('[INFO] Loot below threshold → next')
            search_next()

    state.pause_event.wait()
    if connection_popup_visible():
        print('Connection lost detected—recovering…')
        boot_recovery()
        return

    time.sleep(2)
    state._cycle_count += 1


def bot_loop(cfg):
    sync_state()
    state._switch_attack_counts = {}

    setup_emulator()
    state.pause_event.wait()

    try:
        close_open_panels()
    except Exception as e:
        print(f'[UI] panel check skipped: {e}')

    try:
        from COCbot.attack.api import init_device
        init_device()
    except Exception:
        pass

    state.pause_event.wait()

    # Entry: wait for CoC to load, close any btn_close popup, confirm the
    # Home Village, then zoom out and read its resources.
    try:
        from COCbot.game.village.main_village import prepare_main_village
        resources = prepare_main_village()
        if resources is None:
            print('[VILLAGE] Không xác nhận được làng chính — dừng bot.')
            return
        _notify_resources(resources)
    except Exception as e:
        print(f'[VILLAGE] entry check skipped: {e}')

    # First session: keep using the account already loaded in the game.
    # Reset the time schedule so a stale last_switch_ts cannot switch
    # immediately on startup. Attacks/time/storage conditions still apply
    # later once the bot is running.
    try:
        switch_conf = load_switch_config()
        if switch_conf.get("use_time_schedule"):
            switch_conf["last_switch_ts"] = time.time()
            save_switch_config(switch_conf)
        state._switch_attack_counts = {}
        current = str(switch_conf.get("current_profile", "") or "").strip()
        print(f"[SWITCH] Bắt đầu với account hiện tại"
              f"{': ' + current if current else ''} — không tự chuyển.")
    except Exception as e:
        print(f'[SWITCH] reset startup session skipped: {e}')

    state._cycle_count = 0
    while not state.stop_event.is_set():
        state.pause_event.wait()
        if state.stop_event.is_set():
            break
        one_cycle(cfg)
    print('[INFO] Bot stopped')
    state._saved_wall_offset = None
    state.wall_save = False

def main(config=None):
    try:
        bot_loop(config)
    except KeyboardInterrupt:
        state.stop_event.set()
        print('\n[MAIN] Interrupted by user, exiting...')


if __name__ == '__main__':
    default_config = dict(
        DEFAULT_CFG,
        enable_stats=False,
    )
    main(default_config)
