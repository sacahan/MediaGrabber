"""Integration tests for CLI YouTube pipeline."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from backend.app.cli.main import cli


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


def test_cli_youtube_pipeline_structure(cli_runner: CliRunner) -> None:
    """Test that CLI structure supports YouTube download flow."""
    # Verify all required commands exist
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "download" in result.output
    assert "playlist" in result.output
    assert "status" in result.output
    assert "retry" in result.output
