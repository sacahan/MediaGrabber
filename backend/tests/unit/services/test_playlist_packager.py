"""Playlist packaging tests for partial success scenarios."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from backend.app.models.download_job import DownloadJob
from backend.app.models.playlist_package import PlaylistItemResult
from backend.app.models.transcode_profile import TranscodeProfile, TranscodeProfilePair
from backend.app.services.playlist_packager import PlaylistPackager


@pytest.fixture()
def packager(tmp_path: Path) -> PlaylistPackager:
    return PlaylistPackager(tmp_path)


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
        job_id="playlist-job",
        source_url="https://www.youtube.com/playlist?list=TEST",
        platform="youtube",
        requested_format="zip",
        download_backend="pytubefix",
        profile=profile_pair,
        output_dir=tmp_path,
    )


def _read_summary(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as archive:
        with archive.open("SUMMARY.json") as summary_file:
            return json.load(summary_file)


@pytest.mark.asyncio
async def test_playlist_summary_includes_failed_items(
    packager: PlaylistPackager,
    download_job: DownloadJob,
) -> None:
    """Ensure SUMMARY.json records remediation guidance for failed items."""

    items = [
        PlaylistItemResult(
            index=1,
            title="Track 1",
            status="completed",
            artifact_path=Path("track1.mp4"),
        ),
        PlaylistItemResult(
            index=2,
            title="Track 2",
            status="failed",
            error_code="429",
            error_message="HTTP 429",
            remediation="Wait 60 seconds and retry",
        ),
    ]

    zip_path = await packager.create_playlist_zip(download_job, items)
    summary = _read_summary(zip_path)

    assert summary["failedItems"], "Failed items should be included"
    failed_item = summary["failedItems"][0]
    assert failed_item["status"] == "failed"
    assert failed_item["remediation"] == "Wait 60 seconds and retry"


@pytest.mark.asyncio
async def test_playlist_summary_lists_success_and_failures(
    packager: PlaylistPackager,
    download_job: DownloadJob,
) -> None:
    """SUMMARY.json should clearly separate success/failure and surface suggestions."""

    items = [
        PlaylistItemResult(
            index=1,
            title="Clip A",
            status="completed",
            artifact_path=Path("clip-a.mp4"),
        ),
        PlaylistItemResult(
            index=2,
            title="Clip B",
            status="failed",
            error_code="cookie_required",
            error_message="Login required",
            remediation="Provide cookies via --cookies",
        ),
        PlaylistItemResult(
            index=3,
            title="Clip C",
            status="failed",
            error_code="download_blocked",
            error_message="Geo blocked",
            remediation="Use VPN",
        ),
    ]

    zip_path = await packager.create_playlist_zip(download_job, items)
    summary = _read_summary(zip_path)

    assert len(summary["successItems"]) == 1
    assert len(summary["failedItems"]) == 2
    failed_titles = {item["title"] for item in summary["failedItems"]}
    assert failed_titles == {"Clip B", "Clip C"}

    # Recommendations should consolidate remediation hints for quick CLI display
    recommendations = summary.get("recommendations", [])
    assert "Provide cookies via --cookies" in recommendations
    assert "Use VPN" in recommendations
