# src/run.py
"""Simplicity Bot launcher.

Default: legacy GUI (full farming runtime).
``--mvvm``: new MVVM shell with the migrated settings/accounts/logs/attack/
statistics features.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Launch the requested GUI."""
    if "--mvvm" in sys.argv:
        from COCbot.main import main as mvvm_main

        raise SystemExit(mvvm_main())
    from COCbot.gui.app import main_gui

    main_gui()


if __name__ == "__main__":
    main()
