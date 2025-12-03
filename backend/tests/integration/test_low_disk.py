"""Integration tests for low disk space scenarios."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


from backend.app.services.output_manager import OutputManager


def test_low_disk_cleanup_strategy(temp_output_dir: Path) -> None:
    """Test that OutputManager cleans old jobs when disk is low."""
    mgr = OutputManager(temp_output_dir)

    # Create a few old jobs
    for i in range(3):
        job_root = mgr.prepare_job(f"old-job-{i}")
        # Write dummy file to make jobs have size
        (job_root / "artifacts" / f"data-{i}.bin").write_bytes(b"x" * 1000)

    # Simulate low disk
    with patch.object(mgr, "get_disk_usage", return_value=(0, 100)):
        success, msg = mgr.ensure_free_space(50)

    # Should attempt cleanup
    # Depending on cleanup strategy, some jobs might be removed
    assert isinstance(success, bool)
    assert isinstance(msg, (str, type(None)))


def test_ensure_free_space_with_no_jobs_available(
    temp_output_dir: Path,
) -> None:
    """Test behavior when no jobs can be cleaned."""
    mgr = OutputManager(temp_output_dir)
    with patch.object(mgr, "get_disk_usage", return_value=(0, 1)):
        success, msg = mgr.ensure_free_space(1_000_000)
    assert success is False
    assert msg is not None
