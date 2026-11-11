"""View-models shared by the shell and feature views."""

import COCbot.qt_startup  # noqa: F401  (torch before PyQt5)

from COCbot.viewmodels.base_viewmodel import BaseViewModel
from COCbot.viewmodels.main_viewmodel import MainViewModel

__all__ = ["BaseViewModel", "MainViewModel"]
