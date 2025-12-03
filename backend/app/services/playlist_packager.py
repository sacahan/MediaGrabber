"""Playlist packaging for ZIP generation and manifests."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ..models.download_job import DownloadJob
from ..models.playlist_package import PlaylistItemResult


class PlaylistPackager:
    """Generate ZIP archives with metadata and compression reports."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    async def create_playlist_zip(
        self,
        job: DownloadJob,
        items: list[PlaylistItemResult],
    ) -> Path:
        """Create a ZIP archive containing playlist items and metadata."""
        zip_path = self._output_dir / job.job_id / f"{job.job_id}_playlist.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        # Placeholder: actual ZIP creation would iterate through items
        # and collect successful artifacts
        success_items = [item.as_dict() for item in items if item.status == "completed"]
        failed_items = [item.as_dict() for item in items if item.status != "completed"]
        recommendations = sorted(
            {entry["remediation"] for entry in failed_items if entry.get("remediation")}
        )

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add SUMMARY.json
            summary = {
                "jobId": job.job_id,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "successItems": success_items,
                "failedItems": failed_items,
                "totals": {
                    "items": len(items),
                    "success": len(success_items),
                    "failed": len(failed_items),
                },
                "recommendations": recommendations,
            }
            zf.writestr(
                "SUMMARY.json", json.dumps(summary, ensure_ascii=False, indent=2)
            )

        return zip_path

    def write_compression_report(
        self,
        job: DownloadJob,
        items: list[PlaylistItemResult],
    ) -> Path:
        """Write compression statistics report."""
        report_path = self._output_dir / job.job_id / "COMPRESSION_REPORT.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "Playlist Compression Report",
            f"Job ID: {job.job_id}",
            f"Created: {datetime.now(timezone.utc).isoformat()}",
            "",
            f"Total items: {len(items)}",
            f"Successful: {sum(1 for item in items if item.status == 'completed')}",
            f"Failed: {sum(1 for item in items if item.status != 'completed')}",
        ]

        with report_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return report_path
