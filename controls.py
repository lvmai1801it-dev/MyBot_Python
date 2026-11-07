# ==== controls.py ====
from state import pause_event, stop_event


def pause_bot():
    pause_event.clear()
    print('---------PAUSE---------')


def resume_bot():
    pause_event.set()
    print('---------RESUME---------')


def _check_stop():
    return stop_event.is_set()