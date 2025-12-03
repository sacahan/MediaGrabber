"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from backend.app.services.output_manager import OutputManager
from backend.app.services.progress_bus import ProgressBus


@pytest.fixture()
def temp_output_dir(tmp_path: Path) -> Path:
    path = tmp_path / "output"
    path.mkdir()
    return path


@pytest.fixture()
def output_manager(temp_output_dir: Path) -> OutputManager:
    return OutputManager(temp_output_dir)


@pytest.fixture()
def progress_bus() -> Iterator[ProgressBus]:
    bus = ProgressBus(ttl_seconds=120)
    yield bus
