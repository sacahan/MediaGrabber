"""Structures describing playlist packaging results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(slots=True)
class PlaylistItemResult:
    """Represents the outcome of an item inside a playlist submission."""

    index: int
    title: str
    status: str
    artifact_path: Optional[Path] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    remediation: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "status": self.status,
            "artifactPath": str(self.artifact_path) if self.artifact_path else None,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "remediation": self.remediation,
        }


@dataclass(slots=True)
class PlaylistPackage:
    """Aggregates playlist-wide packaging details including summaries."""

    job_id: str
    zip_path: Optional[Path] = None
    success_items: List[PlaylistItemResult] = field(default_factory=list)
    failed_items: List[PlaylistItemResult] = field(default_factory=list)

    def add_result(self, result: PlaylistItemResult) -> None:
        bucket = (
            self.success_items if result.status == "completed" else self.failed_items
        )
        bucket.append(result)

    def as_summary(self) -> dict:
        return {
            "jobId": self.job_id,
            "zipPath": str(self.zip_path) if self.zip_path else None,
            "successItems": [item.as_dict() for item in self.success_items],
            "failedItems": [item.as_dict() for item in self.failed_items],
        }
