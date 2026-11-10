"""GUI package.

Import torch before PyQt5 on Windows: loading Qt first makes torch's c10.dll
fail to initialise, which also breaks PaddleOCR.
"""
try:
    import torch  # noqa: F401
except Exception:
    pass
