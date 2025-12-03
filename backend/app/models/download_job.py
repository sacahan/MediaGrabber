"""Data structures describing a download/transcode job lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

from .playlist_package import PlaylistItemResult
from .transcode_profile import TranscodeProfilePair

JobStatus = Literal[
    "pending",
    "queued",
    "downloading",
    "transcoding",
    "packaging",
    "cleanup",
    "completed",
    "failed",
]

JobStage = Literal["init", "download", "transcoding", "packaging", "cleanup"]
ArtifactType = Literal["video", "audio", "archive"]


@dataclass(slots=True)
class DownloadError:
    """Structured error payload shared with CLI/REST surfaces."""

    code: str
    message: str
    remediation: Optional[str] = None


@dataclass(slots=True)
class DownloadArtifact:
    """Represents an artifact generated during a job run."""

    job_id: str
    artifact_id: str
    type: ArtifactType
    path: Path
    size_bytes: int
    checksum: Optional[str] = None
    compression_ratio: Optional[float] = None
    expires_at: Optional[datetime] = None

    def as_dict(self) -> dict:
        return {
            "artifactId": self.artifact_id,
            "type": self.type,
            "path": str(self.path),
            "sizeBytes": self.size_bytes,
            "checksum": self.checksum,
            "compressionRatio": self.compression_ratio,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass(slots=True)
class DownloadJob:
    """Canonical representation of a download/transcode request."""

    job_id: str
    source_url: str
    platform: Literal["youtube", "instagram", "facebook", "x"]
    requested_format: Literal["mp4", "mp3", "zip"]
    download_backend: Literal["pytubefix", "yt-dlp"]
    profile: TranscodeProfilePair
    output_dir: Path
    status: JobStatus = "pending"
    stage: JobStage = "init"
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[DownloadError] = None
    playlist_items: Optional[List[PlaylistItemResult]] = None
    artifacts: List[DownloadArtifact] = field(default_factory=list)
    retry_count: int = 0
    queue_wait_seconds: Optional[float] = None
    progress_percent: float = 0.0

    def touch(self) -> None:
        """Refresh the ``updated_at`` timestamp after mutating the job."""

        self.updated_at = datetime.now(timezone.utc)

    def set_status(self, status: JobStatus, stage: Optional[JobStage] = None) -> None:
        self.status = status
        if stage:
            self.stage = stage
        self.touch()

    def record_error(self, error: DownloadError) -> None:
        self.error = error
        self.status = "failed"
        self.touch()

    def add_artifact(self, artifact: DownloadArtifact) -> None:
        self.artifacts.append(artifact)
        self.touch()

    def to_dict(self) -> dict:
        return {
            "jobId": self.job_id,
            "sourceUrl": self.source_url,
            "platform": self.platform,
            "requestedFormat": self.requested_format,
            "downloadBackend": self.download_backend,
            "profile": self.profile.as_dict(),
            "outputDir": str(self.output_dir),
            "status": self.status,
            "stage": self.stage,
            "requestedAt": self.requested_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "error": self.error.__dict__ if self.error else None,
            "playlistItems": [item.as_dict() for item in self.playlist_items]
            if self.playlist_items
            else None,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "retryCount": self.retry_count,
            "queueWaitSeconds": self.queue_wait_seconds,
        }
