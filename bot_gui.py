# ==== src/bot_gui.py (Backward-Compatibility Shim) ====
import COCbot.app.paths  # noqa: F401
from COCbot.gui.app import *

if __name__ == "__main__":
    main_gui()
