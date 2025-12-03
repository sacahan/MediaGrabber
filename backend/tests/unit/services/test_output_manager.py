"""Unit tests for OutputManager disk space management."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.services.output_manager import OutputManager


@pytest.fixture()
def output_manager_with_disk(temp_output_dir: Path) -> OutputManager:
    return OutputManager(temp_output_dir)


def test_prepare_job_creates_subdirs(output_manager_with_disk: OutputManager) -> None:
    job_root = output_manager_with_disk.prepare_job("test-job-1")
    assert (job_root / "artifacts").exists()
    assert (job_root / "tmp").exists()
    assert (job_root / "metadata").exists()


def test_artifact_path_returns_resolved_path(
    output_manager_with_disk: OutputManager,
) -> None:
    path = output_manager_with_disk.artifact_path("job-1", "video.mp4")
    assert path.is_absolute()
    assert "artifacts" in str(path)
    assert "video.mp4" in str(path)


def test_get_disk_usage_returns_tuple(output_manager_with_disk: OutputManager) -> None:
    used, free = output_manager_with_disk.get_disk_usage()
    assert isinstance(used, int)
    assert isinstance(free, int)
    assert used >= 0
    assert free >= 0


def test_ensure_free_space_success_when_plenty(
    output_manager_with_disk: OutputManager,
) -> None:
    with patch.object(
        output_manager_with_disk, "get_disk_usage", return_value=(0, 1_000_000_000)
    ):
        success, msg = output_manager_with_disk.ensure_free_space(100 * 1024 * 1024)
    assert success is True
    assert msg is None


def test_ensure_free_space_failure_insufficient_disk(
    output_manager_with_disk: OutputManager,
) -> None:
    with patch.object(output_manager_with_disk, "get_disk_usage", return_value=(0, 50)):
        success, msg = output_manager_with_disk.ensure_free_space(1024)
    assert success is False
    assert msg is not None
    assert "Insufficient disk space" in msg


def test_cleanup_job_removes_directory(
    output_manager_with_disk: OutputManager,
) -> None:
    output_manager_with_disk.prepare_job("to-delete")
    job_root = output_manager_with_disk.job_root("to-delete")
    assert job_root.exists()
    output_manager_with_disk.cleanup_job("to-delete")
    assert not job_root.exists()
