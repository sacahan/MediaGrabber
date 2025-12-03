"""Async queue wrapper enforcing bounded ffmpeg concurrency."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


class TranscodeQueue(Generic[T]):
    def __init__(self, max_workers: int = 2) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self._max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self._queue_depth = 0
        self._active_workers = 0
        self._lock = asyncio.Lock()

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def queue_depth(self) -> int:
        return self._queue_depth

    @property
    def active_workers(self) -> int:
        return self._active_workers

    async def _enter_queue(self) -> None:
        async with self._lock:
            self._queue_depth += 1

    async def _leave_queue(self) -> None:
        async with self._lock:
            self._queue_depth -= 1

    async def _mark_worker_start(self) -> None:
        async with self._lock:
            self._active_workers += 1

    async def _mark_worker_end(self) -> None:
        async with self._lock:
            self._active_workers -= 1

    async def run(self, work: Callable[[], Awaitable[T]]) -> T:
        await self._enter_queue()
        async with self._semaphore:
            await self._leave_queue()
            await self._mark_worker_start()
            try:
                return await work()
            finally:
                await self._mark_worker_end()

    @asynccontextmanager
    async def worker_slot(self) -> Any:
        """Expose a context manager for code that manages ffmpeg subprocesses."""

        await self._enter_queue()
        async with self._semaphore:
            await self._leave_queue()
            await self._mark_worker_start()
            try:
                yield self
            finally:
                await self._mark_worker_end()
