# ==== src/main.py (Backward-Compatibility Shim) ====
import sys
from types import ModuleType

import COCbot.app.bootstrap as _mod
from COCbot.app import state
from COCbot.app.bootstrap import *

stop_event = state.stop_event
pause_event = state.pause_event


class _MainModule(ModuleType):
    def __getattr__(self, name):
        if hasattr(_mod, name):
            return getattr(_mod, name)
        if hasattr(state, name):
            return getattr(state, name)
        raise AttributeError(f"module 'main' has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in ('host', 'emulator_key', 'ld_index', 'ld_name'):
            setattr(state, name, value)
            setattr(_mod, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _MainModule
