"""Core download service handling YouTube and social platforms."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from ..models.download_job import DownloadJob, DownloadError
from ..models.progress_state import ProgressState
from ..services.retry_policy import RetryPolicy, RetryRemedy
from .progress_bus import ProgressBus


@dataclass(slots=True)
class DownloadResult:
    """Result of a download operation."""

    file_path: Path
    size_bytes: int
    duration_seconds: Optional[float] = None
    error: Optional[DownloadError] = None


class DownloadService:
    """Unified download orchestration for YouTube and social platforms."""

    def __init__(self, progress_bus: ProgressBus) -> None:
        self._bus = progress_bus
        self._retry_policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0)

    async def download_youtube(
        self,
        job: DownloadJob,
        url: str,
    ) -> DownloadResult:
        """Download video from YouTube using pytubefix."""
        # Placeholder implementation
        # This will be filled in with actual pytubefix integration
        await self._publish_progress(
            job, "downloading", "Initializing YouTube download...", 10.0
        )
        return DownloadResult(
            file_path=job.output_dir / "placeholder.mp4",
            size_bytes=0,
        )

    async def download_social(
        self,
        job: DownloadJob,
        url: str,
        cookies_path: Optional[Path] = None,
    ) -> DownloadResult:
        """Download video from Instagram/Facebook/X using yt-dlp."""
        # Placeholder implementation
        # This will be filled in with actual yt-dlp integration
        await self._publish_progress(
            job, "downloading", "Initializing social media download...", 10.0
        )
        return DownloadResult(
            file_path=job.output_dir / "placeholder.mp4",
            size_bytes=0,
        )

    async def download_with_retry(
        self,
        job: DownloadJob,
        url: str,
        cookies_path: Optional[Path] = None,
    ) -> DownloadResult:
        """Download with exponential backoff retry."""

        async def do_download() -> DownloadResult:
            if job.platform == "youtube":
                return await self.download_youtube(job, url)
            else:
                return await self.download_social(job, url, cookies_path)

        async def on_retry(remedy: RetryRemedy) -> None:
            attempts_left = remedy.attempts_remaining
            if attempts_left is None:
                attempts_left = self._retry_policy.attempts_remaining
            attempts_left = max(0, attempts_left)
            countdown = remedy.retry_after_seconds or 1
            msg = f"Platform throttled, retrying in {countdown}s"
            job.retry_count = max(job.retry_count, self._retry_policy.attempt_count)
            await self._publish_progress(
                job,
                "downloading",
                msg,
                max(job.progress_percent, 5.0),
                retry_after_seconds=countdown,
                attempts_remaining=attempts_left,
                remediation=remedy.action or remedy.message,
            )

        try:
            result = await self._retry_policy.execute_with_retry(
                do_download, on_retry=on_retry
            )
            job.retry_count = max(0, self._retry_policy.attempt_count - 1)
            await self._publish_progress(
                job,
                "completed",
                "Download complete",
                100.0,
            )
            return result
        except Exception as exc:
            error = DownloadError(
                code=self._retry_policy.classify_error(exc).value,
                message=str(exc),
                remediation=self._retry_policy.remediation_message(),
            )
            job.retry_count = self._retry_policy.attempt_count
            await self._publish_progress(
                job,
                "failed",
                f"Download failed: {error.message}",
                job.progress_percent,
                remediation=error.remediation,
            )
            return DownloadResult(file_path=Path(), size_bytes=0, error=error)

    async def _publish_progress(
        self,
        job: DownloadJob,
        status: Literal[
            "downloading",
            "transcoding",
            "packaging",
            "failed",
            "completed",
        ],
        message: str,
        percent: float,
        *,
        retry_after_seconds: Optional[int] = None,
        attempts_remaining: Optional[int] = None,
        remediation: Optional[str] = None,
    ) -> None:
        """Publish progress update to bus and keep job percent in sync."""
        job.progress_percent = max(job.progress_percent, percent)
        state = ProgressState(
            job_id=job.job_id,
            status=status,  # type: ignore[arg-type]
            stage=message,
            percent=job.progress_percent,
            message=message,
            retry_after_seconds=retry_after_seconds,
            attempts_remaining=attempts_remaining,
            remediation=remediation,
        )
        self._bus.publish(state)

    @property
    def progress_percent(self) -> Optional[float]:
        """Get current progress percentage."""
        return None
