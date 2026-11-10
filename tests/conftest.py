"""Pytest configuration for the refactored project.

The suite is also runnable with the standard library:
``python -m unittest discover -s tests -t .``
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
