"""Convenience worker for a single heavy task (YOLO, OCR, ADB scan)."""

from __future__ import annotations

from typing import Any, Callable

from COCbot.workers.base_worker import BaseWorker


class TaskWorker(BaseWorker):
    """Thin :class:`BaseWorker` subclass for one-shot tasks."""

    def __init__(
        self,
        target: Callable[..., Any],
        *args: object,
        parent: Any = None,
        pass_cancel_event: bool = False,
        **kwargs: object,
    ) -> None:
        """Create a worker around *target*; see :class:`BaseWorker`."""
        super().__init__(
            target,
            *args,
            parent=parent,
            pass_cancel_event=pass_cancel_event,
            **kwargs,
        )
