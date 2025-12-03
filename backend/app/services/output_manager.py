"""Manage artifact directories and metadata under output/{jobId}."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterable, Optional


class OutputManager:
    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def job_root(self, job_id: str) -> Path:
        return self._root / job_id

    def prepare_job(self, job_id: str) -> Path:
        job_root = self.job_root(job_id)
        (job_root / "artifacts").mkdir(parents=True, exist_ok=True)
        (job_root / "tmp").mkdir(parents=True, exist_ok=True)
        (job_root / "metadata").mkdir(parents=True, exist_ok=True)
        return job_root

    def artifact_path(self, job_id: str, filename: str) -> Path:
        return (self.job_root(job_id) / "artifacts" / filename).resolve()

    def temp_path(self, job_id: str, filename: str) -> Path:
        return (self.job_root(job_id) / "tmp" / filename).resolve()

    def metadata_path(self, job_id: str, filename: str) -> Path:
        return (self.job_root(job_id) / "metadata" / filename).resolve()

    def write_metadata(self, job_id: str, filename: str, payload: Any) -> Path:
        path = self.metadata_path(job_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path

    def write_compression_report(self, job_id: str, lines: Iterable[str]) -> Path:
        path = self.metadata_path(job_id, "COMPRESSION_REPORT.txt")
        with path.open("w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        return path

    def cleanup_job(self, job_id: str) -> None:
        job_root = self.job_root(job_id)
        if job_root.exists():
            shutil.rmtree(job_root, ignore_errors=True)

    def cleanup_all(self) -> None:
        for child in self._root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)

    def list_jobs(self) -> list[Path]:
        return sorted([child for child in self._root.iterdir() if child.is_dir()])

    def oldest_job(self) -> Optional[Path]:
        jobs = self.list_jobs()
        return min(jobs, key=lambda path: path.stat().st_mtime) if jobs else None

    def get_disk_usage(self) -> tuple[int, int]:
        """Return (used, free) bytes on the filesystem hosting root_dir.

        Returns tuple of (used_bytes, free_bytes).
        """
        stat = shutil.disk_usage(self._root)
        return (stat.total - stat.free, stat.free)

    def ensure_free_space(
        self, required_bytes: int, min_free_bytes: int = 100 * 1024 * 1024
    ) -> tuple[bool, Optional[str]]:
        """Ensure sufficient free space; clean old jobs if needed.

        Args:
            required_bytes: Space needed for the new job.
            min_free_bytes: Minimum free space to maintain (default 100 MB).

        Returns:
            Tuple of (success, remediation_message).
            If success is False, remediation_message suggests action.
        """
        used, free = self.get_disk_usage()
        total_needed = required_bytes + min_free_bytes

        if free >= total_needed:
            return (True, None)

        # Try to free space by removing oldest jobs
        freed = 0
        while free + freed < total_needed:
            oldest = self.oldest_job()
            if not oldest:
                msg = (
                    f"Insufficient disk space: {free} bytes free, "
                    f"{required_bytes} bytes required. "
                    "Clear files manually or increase disk space."
                )
                return (False, msg)
            job_size = sum(f.stat().st_size for f in oldest.rglob("*") if f.is_file())
            self.cleanup_job(oldest.name)
            freed += job_size

        return (True, None)
