"""Import torch before PyQt5 on Windows.

Loading Qt first makes torch's ``c10.dll`` fail to initialise, which also
breaks PaddleOCR. Every worker module imports this bootstrap before PyQt5.
"""

from __future__ import annotations

try:
    import torch  # noqa: F401
except Exception:
    pass
