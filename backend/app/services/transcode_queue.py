"""轉碼佇列：強制限制 ffmpeg 並發數的非同步佇列包裝器。

此服務管理轉碼任務的並發執行，防止同時執行過多 ffmpeg 進程，
從而避免系統資源耗盡。使用信號量（semaphore）來控制並發數。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")


class TranscodeQueue(Generic[T]):
    """轉碼佇列：管理轉碼任務的並發執行。

    使用信號量機制限制同時執行的 worker 數量，避免系統過載。
    適用於 CPU 密集型或資源密集型的任務，如 ffmpeg 轉碼。

    屬性:
        _max_workers: 最大並發 worker 數
        _semaphore: asyncio 信號量，用於限制並發數
        _queue_depth: 目前排隊中的任務數
        _active_workers: 目前活躍的 worker 數
        _lock: asyncio 鎖，保護共享狀態
    """

    def __init__(self, max_workers: int = 2) -> None:
        """初始化轉碼佇列。

        Args:
            max_workers: 最大並發 worker 數（預設 2）

        Raises:
            ValueError: 如果 max_workers < 1
        """
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self._max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self._queue_depth = 0  # 佇列深度
        self._active_workers = 0  # 活躍 worker 數
        self._lock = asyncio.Lock()  # 狀態鎖

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
