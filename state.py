# ==== src/state.py (Backward-Compatibility Shim) ====
import sys
import COCbot.core.paths  # noqa: F401
import COCbot.core.state as _state

sys.modules[__name__] = _state
