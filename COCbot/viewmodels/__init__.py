"""Shell-level view-models shared by feature views."""

import COCbot.qt_startup  # noqa: F401  (torch before PyQt5)

from COCbot.viewmodels.base_viewmodel import BaseViewModel

__all__ = ["BaseViewModel"]
