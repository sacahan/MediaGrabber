"""Request validation and schema parsing for API layer."""

from __future__ import annotations

import base64
import json
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
        if self.cookies_base64:
            try:
                # Attempt to decode and validate JSON structure
                decoded = base64.b64decode(self.cookies_base64).decode("utf-8")
                json.loads(decoded)
            except (
                base64.binascii.Error,
                ValueError,
                UnicodeDecodeError,
            ) as e:
                return False, f"Invalid cookies format: {e}"
        return True, None

    def save_cookies_file(self, output_dir: Path) -> Optional[Path]:
        """Save cookies from base64 to temp file."""
        if not self.cookies_base64:
            return None

        try:
            decoded = base64.b64decode(self.cookies_base64).decode("utf-8")
            cookies_path = output_dir / "cookies.txt"
            cookies_path.write_text(decoded)
            return cookies_path
        except Exception:
            return None
