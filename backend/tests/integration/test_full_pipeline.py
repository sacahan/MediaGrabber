"""Integration test for complete download pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.models.download_job import DownloadJob
from backend.app.models.transcode_profile import TranscodeProfile, TranscodeProfilePair
from backend.app.services.progress_bus import ProgressBus
from backend.app.services.output_manager import OutputManager
from backend.app.services.download_service import DownloadService


@pytest.mark.asyncio
async def test_full_pipeline_integrates(temp_output_dir: Path) -> None:
    """Test that all services can work together in a pipeline."""
    # Setup
    bus = ProgressBus(ttl_seconds=120)
    output_mgr = OutputManager(temp_output_dir)
    download_svc = DownloadService(bus)

    # Create a job
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
    profile_pair = TranscodeProfilePair(primary=primary, fallback=fallback)

    job = DownloadJob(
        job_id="integration-test-1",
        source_url="https://www.youtube.com/watch?v=test",
        platform="youtube",
        requested_format="mp4",
        download_backend="pytubefix",
        profile=profile_pair,
        output_dir=output_mgr.prepare_job("integration-test-1"),
    )

    # Execute download
    download_result = await download_svc.download_youtube(job, job.source_url)
    assert download_result is not None

    # Cleanup
    output_mgr.cleanup_job(job.job_id)
    assert not output_mgr.job_root(job.job_id).exists()
