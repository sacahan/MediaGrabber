"""Request validation and schema parsing for API layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class DownloadRequest:
    """Parsed download request from API."""

    url: str
    format: str
    cookies_base64: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict) -> DownloadRequest:
        """Parse from JSON request body."""
        return cls(
            url=data.get("url", ""),
            format=data.get("format", "mp4"),
            cookies_base64=data.get("cookiesBase64"),
        )

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate request parameters."""
        if not self.url:
            return False, "url is required"
        if self.format not in ("mp4", "mp3", "zip"):
            return False, "format must be one of: mp4, mp3, zip"
        return True, None

    def save_cookies_file(self, output_dir: Path) -> Optional[Path]:
        """Save cookies from base64 to temp file."""
        if not self.cookies_base64:
            return None
        # Placeholder: actual base64 decode would go here
        cookies_path = output_dir / "cookies.txt"
        # In real implementation, would decode and write base64
        return cookies_path
