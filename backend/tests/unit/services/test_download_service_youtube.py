"""Unit tests for YouTube download service."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.models.download_job import DownloadJob
from backend.app.models.transcode_profile import TranscodeProfile, TranscodeProfilePair
from backend.app.services.download_service import DownloadService
from backend.app.services.progress_bus import ProgressBus


@pytest.fixture()
def profile_pair() -> TranscodeProfilePair:
    primary = TranscodeProfile(
        name="mobile-primary",
        resolution=(720, 1280),
        video_bitrate_kbps=1000,
        audio_bitrate_kbps=128,
        max_filesize_mb=50,
        crf=23,
        container="mp4",
    )
    fallback = TranscodeProfile(
        name="mobile-fallback",
        resolution=(480, 854),
        video_bitrate_kbps=700,
        audio_bitrate_kbps=96,
        max_filesize_mb=30,
        crf=28,
        container="mp4",
    )
    return TranscodeProfilePair(primary=primary, fallback=fallback)


@pytest.fixture()
def download_job(tmp_path: Path, profile_pair: TranscodeProfilePair) -> DownloadJob:
    return DownloadJob(
        job_id="test-job-1",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        platform="youtube",
        requested_format="mp4",
        download_backend="pytubefix",
        profile=profile_pair,
        output_dir=tmp_path,
    )


@pytest.mark.asyncio
async def test_download_service_initializes(progress_bus: ProgressBus) -> None:
    service = DownloadService(progress_bus)
    assert service is not None


@pytest.mark.asyncio
async def test_download_youtube_returns_result(
    progress_bus: ProgressBus,
    download_job: DownloadJob,
) -> None:
    service = DownloadService(progress_bus)
    result = await service.download_youtube(download_job, download_job.source_url)
    assert result is not None
    assert result.file_path is not None
