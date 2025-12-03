"""CLI entry point for MediaGrabber with download/playlist/retry/status commands."""

from __future__ import annotations

import click


@click.group()
def cli() -> None:
    """MediaGrabber CLI - Download media from YouTube and social platforms."""
    pass


@cli.command()
@click.option("--url", required=True, help="Media URL to download")
@click.option("--format", type=click.Choice(["mp4", "mp3"]), default="mp4")
def download(url: str, format: str) -> None:
    """Download a single media item."""
    click.echo(f"Downloading {url} as {format}...")
    # Placeholder - actual implementation follows


@cli.command()
@click.option("--url", required=True, help="Playlist URL to download")
@click.option("--format", type=click.Choice(["mp4", "mp3", "zip"]), default="zip")
def playlist(url: str, format: str) -> None:
    """Download a playlist as individual items or ZIP."""
    click.echo(f"Downloading playlist {url} as {format}...")
    # Placeholder - actual implementation follows


@cli.command()
@click.option("--job-id", required=True, help="Job ID to query")
def status(job_id: str) -> None:
    """Query status of a download job."""
    click.echo(f"Status of job {job_id}...")
    # Placeholder - actual implementation follows


@cli.command()
@click.option("--job-id", required=True, help="Job ID to retry")
def retry(job_id: str) -> None:
    """Retry a failed download job."""
    click.echo(f"Retrying job {job_id}...")
    # Placeholder - actual implementation follows


if __name__ == "__main__":
    cli()
