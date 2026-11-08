# ==== src/bot_gui.py (Backward-Compatibility Shim) ====
import COCbot.core.paths  # noqa: F401
from COCbot.gui.bot_gui import *

if __name__ == "__main__":
    main_gui()
