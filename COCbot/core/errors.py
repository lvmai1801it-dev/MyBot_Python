"""Typed exceptions for the application and infrastructure layers."""

from __future__ import annotations


class BotError(Exception):
    """Base class for every expected application error."""


class ConfigError(BotError):
    """Raised when a configuration value is missing or invalid."""


class AdbError(BotError):
    """Raised when an ADB command cannot be executed."""


class EmulatorError(BotError):
    """Raised when an emulator cannot be discovered or controlled."""


class CaptureError(BotError):
    """Raised when a screen capture cannot be obtained."""


class VisionError(BotError):
    """Raised when YOLO/OpenCV inference fails."""


class OcrError(BotError):
    """Raised when an OCR engine fails."""


class AttackError(BotError):
    """Raised when an attack cycle cannot complete."""


class AccountError(BotError):
    """Raised when a shared_prefs account operation fails."""


class StorageError(BotError):
    """Raised when settings, profiles, or stats cannot be persisted."""


class WorkerError(BotError):
    """Raised when a background worker stops unexpectedly."""
