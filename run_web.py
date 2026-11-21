# src/run_web.py
"""Launch the pywebview front-end (same bot runtime as run.py).

The Qt GUI stays the default entry point; this shell is the web-based
alternative. Both read/write the same settings.json and drive the same
bot_loop, so they can be swapped freely.
"""

from __future__ import annotations

from COCbot.webui.app import run


if __name__ == "__main__":
    run()
