"""CLI integration tests for throttling and retry scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.cli.progress_renderer import ProgressRenderer
from backend.app.models.download_job import DownloadJob
from backend.app.models.transcode_profile import TranscodeProfile, TranscodeProfilePair
from backend.app.services.download_service import DownloadResult, DownloadService
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


def _make_job(tmp_path: Path, profile_pair: TranscodeProfilePair) -> DownloadJob:
    return DownloadJob(
        job_id="cli-test-job",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        platform="youtube",
        requested_format="mp4",
        download_backend="pytubefix",
        profile=profile_pair,
        output_dir=tmp_path,
    )


@pytest.mark.asyncio
async def test_cli_retry_backoff_on_429(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    progress_bus: ProgressBus,
    profile_pair: TranscodeProfilePair,
) -> None:
    """Ensure retry policy emits backoff telemetry on HTTP 429 errors."""

    renderer = ProgressRenderer()
    recorded_states = []
    progress_bus.subscribe(renderer.render)
    progress_bus.subscribe(recorded_states.append)

    service = DownloadService(progress_bus)
    job = _make_job(tmp_path, profile_pair)
    attempts = {"count": 0}

    async def _flaky_download(
        self: DownloadService, job: DownloadJob, url: str
    ) -> DownloadResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise Exception("HTTP 429: Too Many Requests")
        return DownloadResult(file_path=job.output_dir / "video.mp4", size_bytes=1024)

    monkeypatch.setattr(DownloadService, "download_youtube", _flaky_download)

    result = await service.download_with_retry(job, job.source_url)
    assert result.error is None
    assert attempts["count"] == 2

    throttled_states = [state for state in recorded_states if state.retry_after_seconds]
    assert throttled_states, "Expected progress events with retry metadata"
    assert throttled_states[0].attempts_remaining >= 0


@pytest.mark.asyncio
async def test_cli_shows_retry_countdown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    progress_bus: ProgressBus,
    profile_pair: TranscodeProfilePair,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify progress renderer surfaces retry countdown details to the CLI."""

    renderer = ProgressRenderer()
    progress_bus.subscribe(renderer.render)

    service = DownloadService(progress_bus)
    job = _make_job(tmp_path, profile_pair)
    attempts = {"count": 0}

    async def _sometimes_flaky(
        self: DownloadService, job: DownloadJob, url: str
    ) -> DownloadResult:
        attempts["count"] += 1
        if attempts["count"] <= 2:
            raise Exception("HTTP 429: Too Many Requests")
        return DownloadResult(file_path=job.output_dir / "video.mp4", size_bytes=1024)

    monkeypatch.setattr(DownloadService, "download_youtube", _sometimes_flaky)

    result = await service.download_with_retry(job, job.source_url)
    assert result.error is None
    output = capsys.readouterr().out
    assert "Retry" in output and "s" in output, output


@pytest.mark.asyncio
async def test_cli_shows_remediation_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    progress_bus: ProgressBus,
    profile_pair: TranscodeProfilePair,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure remediation advice is surfaced when retries are exhausted."""

    renderer = ProgressRenderer()
    progress_bus.subscribe(renderer.render)

    service = DownloadService(progress_bus)
    job = _make_job(tmp_path, profile_pair)

    async def _always_fail(
        self: DownloadService, job: DownloadJob, url: str
    ) -> DownloadResult:
        raise Exception("HTTP 429: Too Many Requests")

    monkeypatch.setattr(DownloadService, "download_youtube", _always_fail)

    result = await service.download_with_retry(job, job.source_url)
    assert result.error is not None
    assert result.error.remediation is not None

    output = capsys.readouterr().out
    assert "Platform" in output or "remediation" in output or "retry" in output
