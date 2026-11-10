# ==== src/state.py (Backward-Compatibility Shim) ====
import sys
import COCbot.app.paths  # noqa: F401
import COCbot.app.state as _state

sys.modules[__name__] = _state
