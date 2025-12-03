"""Transcode profile definitions for primary and fallback presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple


@dataclass(slots=True)
class TranscodeProfile:
    name: Literal["mobile-primary", "mobile-fallback"]
    resolution: Tuple[int, int]
    video_bitrate_kbps: int
    audio_bitrate_kbps: int
    max_filesize_mb: int
    crf: int
    container: Literal["mp4", "mp3"]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "resolution": self.resolution,
            "videoBitrateKbps": self.video_bitrate_kbps,
            "audioBitrateKbps": self.audio_bitrate_kbps,
            "maxFilesizeMb": self.max_filesize_mb,
            "crf": self.crf,
            "container": self.container,
        }


@dataclass(slots=True)
class TranscodeProfilePair:
    primary: TranscodeProfile
    fallback: TranscodeProfile

    def as_dict(self) -> dict:
        return {
            "primary": self.primary.as_dict(),
            "fallback": self.fallback.as_dict(),
        }
