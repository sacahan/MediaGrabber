"""進度匯流排：跨 CLI 和 REST API 共用的記憶體內進度事件匯流排。

此服務提供了一個輕量級的發佈/訂閱機制，用於在系統內傳遞進度更新。
支援多個訂閱者同時接收進度更新，並快取每個任務的最新狀態。
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List, Optional

from ..models.progress_state import ProgressState

# 進度回調函式類型：接收 ProgressState 並處理
ProgressCallback = Callable[[ProgressState], None]


class ProgressBus:
    """進度匯流排：將進度事件廣播給訂閱者，並快取每個任務的最新狀態。

    此類別實現了發佈-訂閱模式，支援：
    - 多個訂閱者同時接收更新
    - 自動快取和過期清理
    - 執行緒安全的操作

    屬性:
        _ttl_seconds: 進度狀態的生存時間（秒）
        _clock: 時鐘函式
        _subscribers: 訂閱者清單
        _store: 快取儲存器，存放最新的進度狀態
        _lock: 執行緒鎖，確保執行緒安全
    """

    def __init__(
        self, ttl_seconds: int, clock: Callable[[], float] | None = None
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock or time.time
        self._subscribers: List[ProgressCallback] = []
        self._store: Dict[str, tuple[ProgressState, float]] = {}
        self._lock = threading.Lock()

    def publish(self, state: ProgressState) -> None:
        state.clamp_percent()
        with self._lock:
            now = self._clock()
            self._store[state.job_id] = (state, now)
            self._evict_expired(now)
            listeners = list(self._subscribers)
        for callback in listeners:
            callback(state)

    def subscribe(self, callback: ProgressCallback) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: ProgressCallback) -> None:
        with self._lock:
            self._subscribers = [cb for cb in self._subscribers if cb is not callback]

    def latest(self, job_id: str) -> Optional[ProgressState]:
        with self._lock:
            entry = self._store.get(job_id)
            if not entry:
                return None
            state, timestamp = entry
            if self._clock() - timestamp > self._ttl_seconds:
                self._store.pop(job_id, None)
                return None
            return state

    def snapshot(self) -> Dict[str, ProgressState]:
        with self._lock:
            now = self._clock()
            self._evict_expired(now)
            return {job_id: state for job_id, (state, _) in self._store.items()}

    def _evict_expired(self, now: float) -> None:
        expired = [
            job_id
            for job_id, (_, timestamp) in self._store.items()
            if now - timestamp > self._ttl_seconds
        ]
        for job_id in expired:
            self._store.pop(job_id, None)
