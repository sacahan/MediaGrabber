"""Progress telemetry dataclass shared across CLI and REST."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

ProgressStatus = Literal[
    "queued",
    "downloading",
    "transcoding",
    "packaging",
    "completed",
    "failed",
]


@dataclass(slots=True)
class ProgressState:
    job_id: str
    status: ProgressStatus
    stage: str
    percent: float
    message: str = ""
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed: Optional[float] = None
    eta_seconds: Optional[int] = None
    retry_after_seconds: Optional[int] = None
    attempts_remaining: Optional[int] = None
    remediation: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def clamp_percent(self) -> None:
        self.percent = max(0.0, min(100.0, self.percent))

    def with_message(self, message: str) -> "ProgressState":
        self.message = message
        return self
