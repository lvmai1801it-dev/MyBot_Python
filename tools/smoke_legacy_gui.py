"""Offscreen smoke: boot the legacy GUI (the only entry point now)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QTimer  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from COCbot.gui.app import MainWindow  # noqa: E402


def main() -> int:
    app = QApplication([])
    window = MainWindow()
    QTimer.singleShot(1500, app.quit)
    app.exec_()
    print("LEGACY GUI SMOKE OK — python run.py boots, tabs built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
