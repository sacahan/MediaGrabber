"""In-memory progress event bus shared across CLI and REST."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List, Optional

from ..models.progress_state import ProgressState

ProgressCallback = Callable[[ProgressState], None]


class ProgressBus:
    """Fan-out progress events to subscribers and cache the latest per job."""

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
