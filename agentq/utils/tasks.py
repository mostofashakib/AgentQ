from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from types import TracebackType
from typing import Any


class BackgroundTaskGroup:
    """Own application worker tasks and shut them down deterministically."""

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[Any]] = []
        self._logger = logging.getLogger(__name__)

    async def __aenter__(self) -> "BackgroundTaskGroup":
        return self

    def start(self, coroutine: Coroutine[Any, Any, Any], *, name: str) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine, name=name)
        self._tasks.append(task)
        return task

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for task in self._tasks:
            task.cancel()
        results = await asyncio.gather(*self._tasks, return_exceptions=True)
        for task, result in zip(self._tasks, results, strict=True):
            if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
                self._logger.error(
                    "Background task %s failed during shutdown",
                    task.get_name(),
                    exc_info=(type(result), result, result.__traceback__),
                )
