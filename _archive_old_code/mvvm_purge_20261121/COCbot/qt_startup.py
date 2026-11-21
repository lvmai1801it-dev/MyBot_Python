"""Import torch before PyQt5 on Windows.

Loading Qt first makes torch's ``c10.dll`` fail to initialise, which also
breaks PaddleOCR. UI packages import this module before importing PyQt5.
"""

from __future__ import annotations

try:
    import torch  # noqa: F401
except Exception:
    pass
