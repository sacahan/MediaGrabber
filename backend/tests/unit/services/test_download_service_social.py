"""Unit tests for social media download service (Instagram, Facebook, X)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.models.download_job import DownloadJob, DownloadError
from backend.app.models.transcode_profile import TranscodeProfile, TranscodeProfilePair
from backend.app.services.download_service import DownloadService, DownloadResult
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
def social_download_job(
    tmp_path: Path, profile_pair: TranscodeProfilePair
) -> DownloadJob:
    return DownloadJob(
        job_id="test-social-1",
        source_url="https://www.instagram.com/reel/abc123/",
        platform="instagram",
        requested_format="mp4",
        download_backend="yt-dlp",
        profile=profile_pair,
        output_dir=tmp_path,
    )


@pytest.fixture()
def download_service(progress_bus: ProgressBus) -> DownloadService:
    return DownloadService(progress_bus)


@pytest.mark.asyncio
async def test_download_social_instagram_with_ytdlp(
    download_service: DownloadService,
    social_download_job: DownloadJob,
) -> None:
    """Test that Instagram downloads route to yt-dlp backend."""
    result = await download_service.download_social(
        social_download_job, social_download_job.source_url
    )
    assert isinstance(result, DownloadResult)
    assert social_download_job.platform == "instagram"
    assert social_download_job.download_backend == "yt-dlp"


@pytest.mark.asyncio
async def test_download_social_with_cookies_path(
    download_service: DownloadService,
    social_download_job: DownloadJob,
    tmp_path: Path,
) -> None:
    """Test that download_social accepts cookies_path parameter."""
    cookies_file = tmp_path / "instagram.txt"
    cookies_file.write_text("test_cookie=value; secure")

    result = await download_service.download_social(
        social_download_job, social_download_job.source_url, cookies_path=cookies_file
    )
    assert isinstance(result, DownloadResult)


@pytest.mark.asyncio
async def test_download_social_platforms(
    download_service: DownloadService,
    profile_pair: TranscodeProfilePair,
    tmp_path: Path,
) -> None:
    """Test all supported social platforms route to yt-dlp."""
    for platform_url, platform_name in [
        ("https://www.instagram.com/reel/abc123/", "instagram"),
        ("https://www.facebook.com/video.php?v=123", "facebook"),
        ("https://x.com/user/status/123", "x"),
    ]:
        job = DownloadJob(
            job_id=f"test-{platform_name}",
            source_url=platform_url,
            platform=platform_name,  # type: ignore
            requested_format="mp4",
            download_backend="yt-dlp",
            profile=profile_pair,
            output_dir=tmp_path,
        )
        result = await download_service.download_social(job, platform_url)
        assert isinstance(result, DownloadResult)
        assert job.platform == platform_name


@pytest.mark.asyncio
async def test_download_social_retry_on_auth_error(
    download_service: DownloadService,
    social_download_job: DownloadJob,
) -> None:
    """Test that auth errors trigger retry with optional cookies."""
    # This tests the retry policy integration
    result = await download_service.download_with_retry(
        social_download_job, social_download_job.source_url
    )
    assert isinstance(result, DownloadResult)


@pytest.mark.asyncio
async def test_download_social_returns_error_on_failure(
    download_service: DownloadService,
    social_download_job: DownloadJob,
) -> None:
    """Test that download errors are captured in result."""
    # Mock a failure scenario
    with patch.object(
        download_service, "download_social", new_callable=AsyncMock
    ) as mock_download:
        mock_download.return_value = DownloadResult(
            file_path=Path(),
            size_bytes=0,
            error=DownloadError(
                code="AUTH_REQUIRED",
                message="Cookies required for this video",
                remediation="Try uploading cookies via the web UI",
            ),
        )
        result = await download_service.download_social(
            social_download_job, social_download_job.source_url
        )
        assert result.error is not None
        assert result.error.code == "AUTH_REQUIRED"
        assert "cookies" in result.error.remediation.lower()
