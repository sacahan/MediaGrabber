"""Contract tests for CLI commands."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from backend.app.cli.main import cli


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


def test_download_command_shows_help(cli_runner: CliRunner) -> None:
    """Test that download command accepts --help."""
    result = cli_runner.invoke(cli, ["download", "--help"])
    assert result.exit_code == 0
    assert "Media URL" in result.output or "url" in result.output.lower()


def test_playlist_command_shows_help(cli_runner: CliRunner) -> None:
    """Test that playlist command accepts --help."""
    result = cli_runner.invoke(cli, ["playlist", "--help"])
    assert result.exit_code == 0
    assert "playlist" in result.output.lower()


def test_status_command_shows_help(cli_runner: CliRunner) -> None:
    """Test that status command accepts --help."""
    result = cli_runner.invoke(cli, ["status", "--help"])
    assert result.exit_code == 0
    assert "job" in result.output.lower()


def test_retry_command_shows_help(cli_runner: CliRunner) -> None:
    """Test that retry command accepts --help."""
    result = cli_runner.invoke(cli, ["retry", "--help"])
    assert result.exit_code == 0
    assert "job" in result.output.lower()


def test_download_command_requires_url(cli_runner: CliRunner) -> None:
    """Test that download command requires --url parameter."""
    result = cli_runner.invoke(cli, ["download"])
    assert result.exit_code != 0
    assert "missing" in result.output.lower() or "required" in result.output.lower()
