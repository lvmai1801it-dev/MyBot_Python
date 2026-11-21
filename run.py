# src/run.py
"""Simplicity Bot launcher.

Runs the legacy GUI (the full farming runtime: training, collectors,
auto-upgrades via the Build panel, ONNX redline attacks, account
switching). The experimental MVVM shell was removed for good.
"""

from __future__ import annotations

from COCbot.gui.app import main_gui


def main() -> None:
    """Launch the GUI."""
    main_gui()


if __name__ == "__main__":
    main()
