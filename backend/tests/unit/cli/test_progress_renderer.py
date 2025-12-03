"""Unit tests for CLI progress renderer summary output."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.cli.progress_renderer import ProgressRenderer
from backend.app.models.playlist_package import PlaylistItemResult


@pytest.fixture()
def playlist_items(tmp_path: Path) -> list[PlaylistItemResult]:
    return [
        PlaylistItemResult(
            index=1,
            title="Video A",
            status="completed",
            artifact_path=tmp_path / "video-a.mp4",
        ),
        PlaylistItemResult(
            index=2,
            title="Video B",
            status="failed",
            error_code="cookie_required",
            error_message="Authentication needed",
            remediation="Provide cookies",
        ),
    ]


def test_render_summary_prints_failed_items(
    playlist_items: list[PlaylistItemResult], capsys: pytest.CaptureFixture[str]
) -> None:
    renderer = ProgressRenderer()
    renderer.render_summary(playlist_items, recommendations=["Provide cookies"])

    output = capsys.readouterr().out
    assert "Failed items" in output
    assert "Video B" in output
    assert "Provide cookies" in output
