"""CLI entry point for MediaGrabber with download/playlist/retry/status commands."""

from __future__ import annotations

import click
from pathlib import Path


@click.group()
def cli() -> None:
    """MediaGrabber CLI - Download media from YouTube and social platforms."""
    pass


@cli.command()
@click.option("--url", required=True, help="Media URL to download")
@click.option("--format", type=click.Choice(["mp4", "mp3"]), default="mp4")
@click.option(
    "--cookies",
    type=click.Path(exists=True, path_type=Path),
    help="Path to Netscape format cookies.txt file (required for Threads)",
)
def download(url: str, format: str, cookies: Path | None) -> None:
    """Download a single media item.

    Supports YouTube, Instagram, Facebook, X (Twitter), and Threads.
    For Threads downloads, you must provide a --cookies file with valid
    Instagram/Threads session cookies.

    Examples:
        mediagrabber download --url "https://www.youtube.com/watch?v=..." --format mp3
        mediagrabber download --url "https://www.threads.net/@user/post/..." --cookies cookies.txt
    """
    # Detect platform from URL
    from urllib.parse import urlparse

    parsed = urlparse(url)
    netloc = parsed.netloc.lower()

    platform = None
    if "youtube.com" in netloc or "youtu.be" in netloc:
        platform = "youtube"
    elif "instagram.com" in netloc:
        platform = "instagram"
    elif "facebook.com" in netloc:
        platform = "facebook"
    elif "x.com" in netloc or "twitter.com" in netloc:
        platform = "x"
    elif "threads.net" in netloc or "threads.com" in netloc:
        platform = "threads"

    if platform is None:
        click.echo(click.style("Error: Unsupported platform", fg="red"))
        click.echo(
            "Supported platforms: YouTube, Instagram, Facebook, X (Twitter), Threads"
        )
        raise SystemExit(1)

    # Validate Threads requires cookies
    if platform == "threads" and cookies is None:
        # Check for default cookies files
        default_threads = (
            Path(__file__).parent.parent.parent / "cookies" / "threads.txt"
        )
        default_instagram = (
            Path(__file__).parent.parent.parent / "cookies" / "instagram.txt"
        )

        if default_threads.exists():
            cookies = default_threads
            click.echo(f"Using default Threads cookies: {cookies}")
        elif default_instagram.exists():
            cookies = default_instagram
            click.echo(f"Using default Instagram cookies for Threads: {cookies}")
        else:
            click.echo(
                click.style(
                    "Warning: Threads download requires cookies for authentication",
                    fg="yellow",
                )
            )
            click.echo(
                "Use --cookies to provide a cookies.txt file, or place cookies at:"
            )
            click.echo(f"  - {default_threads}")
            click.echo(f"  - {default_instagram}")

    click.echo(f"Downloading {url} as {format}...")
    if cookies:
        click.echo(f"Using cookies from: {cookies}")

    # TODO: Implement actual download logic using yt-dlp
    # This is a placeholder - actual implementation follows


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
