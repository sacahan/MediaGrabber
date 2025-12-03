"""Environment-backed application settings loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    max_transcode_workers: int
    output_dir: Path
    progress_ttl_seconds: int


def _read_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    max_workers = _read_int("MG_MAX_TRANSCODE_WORKERS", default=2, minimum=1)
    ttl_seconds = _read_int("MG_PROGRESS_TTL_SECONDS", default=300, minimum=60)
    output_dir = Path(os.environ.get("MG_OUTPUT_DIR", "output")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return AppSettings(
        max_transcode_workers=max_workers,
        output_dir=output_dir,
        progress_ttl_seconds=ttl_seconds,
    )


def reset_settings_cache() -> None:
    """Clear memoized settings (useful for tests)."""

    load_settings.cache_clear()
