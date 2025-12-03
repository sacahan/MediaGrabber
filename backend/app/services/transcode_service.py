"""Transcode service handling ffmpeg operations with queue management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from ..models.download_job import DownloadJob, DownloadError
from ..models.transcode_profile import TranscodeProfilePair
from ..services.progress_bus import ProgressBus
from ..services.retry_policy import RetryPolicy, RetryRemedy
from ..services.transcode_queue import TranscodeQueue


@dataclass(slots=True)
class TranscodeResult:
    """Result of a transcode operation."""

    output_path: Path
    size_bytes: int
    compression_ratio: float = 0.0
    error: Optional[DownloadError] = None


class TranscodeService:
    """Handle ffmpeg-based transcoding with queue management."""

    def __init__(
        self,
        queue: TranscodeQueue,
        progress_bus: ProgressBus,
    ) -> None:
        self._queue = queue
        self._bus = progress_bus
        self._retry_policy = RetryPolicy(max_attempts=2, base_delay_seconds=1.0)

    async def transcode_primary(
        self,
        job: DownloadJob,
        input_path: Path,
        output_path: Path,
        profile: TranscodeProfilePair,
    ) -> TranscodeResult:
        """Transcode with primary profile, optionally fall back to fallback profile."""

        async def do_transcode() -> TranscodeResult:
            # Publish progress
            await self._publish_progress(
                job, "transcoding", "Starting primary transcode...", 20.0
            )

            # Placeholder: actual ffmpeg execution would go here
            # For now, just return a mock result
            return TranscodeResult(
                output_path=output_path,
                size_bytes=0,
                compression_ratio=0.0,
            )

        async def on_retry(remedy: RetryRemedy) -> None:
            msg = f"Transcode retry: {remedy.message}"
            await self._publish_progress(job, "transcoding", msg, 20.0)

        try:
            result = await self._retry_policy.execute_with_retry(
                do_transcode, on_retry=on_retry
            )

            # Check if result exceeds max filesize; if so, try fallback
            if result.size_bytes > profile.primary.max_filesize_mb * 1024 * 1024:
                result = await self.transcode_fallback(
                    job, input_path, output_path, profile
                )

            return result
        except Exception as exc:
            error = DownloadError(
                code=self._retry_policy.classify_error(exc).value,
                message=str(exc),
                remediation=self._retry_policy.remediation_message(),
            )
            return TranscodeResult(output_path=Path(), size_bytes=0, error=error)

    async def transcode_fallback(
        self,
        job: DownloadJob,
        input_path: Path,
        output_path: Path,
        profile: TranscodeProfilePair,
    ) -> TranscodeResult:
        """Transcode with fallback profile."""
        await self._publish_progress(
            job, "transcoding", "Trying fallback profile...", 40.0
        )
        # Placeholder implementation
        return TranscodeResult(
            output_path=output_path,
            size_bytes=0,
            compression_ratio=0.0,
        )

    async def transcode_with_queue(
        self,
        job: DownloadJob,
        input_path: Path,
        output_path: Path,
        profile: TranscodeProfilePair,
    ) -> TranscodeResult:
        """Queue the transcode job and execute with bounded concurrency."""

        async def work() -> TranscodeResult:
            return await self.transcode_primary(job, input_path, output_path, profile)

        async with self._queue.worker_slot():
            return await work()

    async def _publish_progress(
        self,
        job: DownloadJob,
        status: Literal["transcoding"],
        message: str,
        percent: float,
    ) -> None:
        """Publish progress to bus."""
        from ..models.progress_state import ProgressState

        state = ProgressState(
            job_id=job.job_id,
            status=status,  # type: ignore
            stage=message,
            percent=percent,
            message=message,
        )
        self._bus.publish(state)
