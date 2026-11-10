"""Log record formatters."""

from __future__ import annotations

import logging

from COCbot.core.config.defaults import LOG_MESSAGE_FORMAT, LOG_TIME_FORMAT

SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


class BotFormatter(logging.Formatter):
    """Compact one-line formatter used by console and rotating file handlers."""

    def __init__(
        self,
        fmt: str = LOG_MESSAGE_FORMAT,
        datefmt: str = LOG_TIME_FORMAT,
    ) -> None:
        """Create a formatter with the project's default layout."""
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """Format *record* and collapse embedded newlines for table output."""
        text = super().format(record)
        return text.replace("\r\n", "\n").replace("\n", " | ")
