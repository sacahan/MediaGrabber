"""Progress store for maintaining job history and telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..models.progress_state import ProgressState


@dataclass(slots=True)
class ProgressRecord:
    """A single progress record with timestamp."""

    state: ProgressState
    timestamp: datetime = field(default_factory=datetime.now)


class ProgressStore:
    """Maintain TTL-based progress history for jobs."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        """Initialize progress store with TTL."""
        self._ttl_seconds = ttl_seconds
        self._records: dict[str, list[ProgressRecord]] = {}

    def record(self, state: ProgressState) -> None:
        """Record a progress state update."""
        job_id = state.job_id
        if job_id not in self._records:
            self._records[job_id] = []

        record = ProgressRecord(state=state)
        self._records[job_id].append(record)

    def get_latest(self, job_id: str) -> Optional[ProgressState]:
        """Get the most recent progress state for a job."""
        if job_id not in self._records:
            return None

        records = self._get_valid_records(job_id)
        if records:
            return records[-1].state
        return None

    def get_history(self, job_id: str, limit: int = 100) -> list[ProgressState]:
        """Get progress history for a job."""
        if job_id not in self._records:
            return []

        records = self._get_valid_records(job_id)
        return [r.state for r in records[-limit:]]

    def get_queue_depth(self) -> int:
        """Get current queue depth (jobs in queued/transcoding status)."""
        count = 0
        now = datetime.now()
        expiry = timedelta(seconds=self._ttl_seconds)

        for records in self._records.values():
            for record in records:
                if now - record.timestamp < expiry and record.state.status in (
                    "queued",
                    "transcoding",
                ):
                    count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove expired records and return count of expired jobs."""
        expired_count = 0
        now = datetime.now()
        expiry = timedelta(seconds=self._ttl_seconds)

        jobs_to_delete = []
        for job_id, records in self._records.items():
            valid_records = [r for r in records if now - r.timestamp < expiry]
            if not valid_records:
                jobs_to_delete.append(job_id)
            else:
                self._records[job_id] = valid_records
                if len(valid_records) < len(records):
                    expired_count += len(records) - len(valid_records)

        for job_id in jobs_to_delete:
            del self._records[job_id]
            expired_count += 1

        return expired_count

    def _get_valid_records(self, job_id: str) -> list[ProgressRecord]:
        """Get valid (non-expired) records for a job."""
        if job_id not in self._records:
            return []

        now = datetime.now()
        expiry = timedelta(seconds=self._ttl_seconds)

        return [r for r in self._records[job_id] if now - r.timestamp < expiry]
