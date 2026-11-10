"""Logger factory with console and rotating-file handlers.

The logger is intentionally built from :class:`LoggingConfig` so the UI can
change level/destination without touching logging internals.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from COCbot.core.config.paths import get_project_paths
from COCbot.core.config.schema import LoggingConfig
from COCbot.core.logging.formatters import SUCCESS_LEVEL, BotFormatter

_CONFIGURED: set[str] = set()


def _resolve_log_path(file_path: str) -> Path:
    """Resolve a configured log path relative to the project ``src`` root."""
    path = Path(file_path).expanduser()
    if path.is_absolute():
        return path
    return get_project_paths().src_dir / path


def build_logger(
    name: str = "mybot",
    config: LoggingConfig | None = None,
) -> logging.Logger:
    """Return a configured logger, creating handlers only once per name."""
    logger = logging.getLogger(name)
    if name in _CONFIGURED:
        return logger

    cfg = config or LoggingConfig()
    level = getattr(logging, cfg.level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = BotFormatter()

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if cfg.file_enabled:
        log_path = _resolve_log_path(cfg.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=cfg.max_bytes,
            backupCount=cfg.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _CONFIGURED.add(name)
    return logger


def get_logger(name: str = "mybot") -> logging.Logger:
    """Return an existing logger without creating handlers."""
    return logging.getLogger(name)


def reset_logger(name: str = "mybot") -> None:
    """Remove handlers and allow :func:`build_logger` to rebuild the logger."""
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    _CONFIGURED.discard(name)


def log_success(logger: logging.Logger, message: str, *args: object, **kwargs: object) -> None:
    """Log at the custom ``SUCCESS`` level used by the bot log."""
    logger.log(SUCCESS_LEVEL, message, *args, **kwargs)
