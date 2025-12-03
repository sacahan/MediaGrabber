# MediaGrabber Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-02

## Active Technologies

- Backend Python 3.12 + Flask 2.x; Frontend Svelte 5 + TypeScript; ffmpeg 4.x for media ops. + pytubefix 10.3.5+, yt-dlp 2025.0+, ffmpeg CLI, click/argparse for CLI entry, Vite build tool, Tailwind CSS. (002-download-refactor)
- Local filesystem under `output/{jobId}` plus transient temp dirs; no database involvement this iteration. (002-download-refactor)

- Python 3.10+ (currently 3.11.13) + pytubefix 10.3.5+, yt-dlp 2025.11.29+, Flask 2.0+, ffmpeg 7.1+ (001-download-refactor)
- Local filesystem (output files) (001-download-refactor)

- Python 3.11+ + pytubefix (10.3.5+), yt-dlp (2025.11.29+), Flask (2.0+), FFmpeg (4.0+) (001-download-refactor)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- 002-download-refactor: Added Backend Python 3.12 + Flask 2.x; Frontend Svelte 5 + TypeScript; ffmpeg 4.x for media ops. + pytubefix 10.3.5+, yt-dlp 2025.0+, ffmpeg CLI, click/argparse for CLI entry, Vite build tool, Tailwind CSS.
- 001-download-refactor: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

- 001-download-refactor: Added Python 3.10+ (currently 3.11.13) + pytubefix 10.3.5+, yt-dlp 2025.11.29+, Flask 2.0+, ffmpeg 7.1+

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
