# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaGrabber is a media downloader application that supports YouTube (MP3/MP4), Facebook, Instagram, and Threads videos. It consists of:

- **Backend**: Python Flask REST API using `yt-dlp` for media downloading and `ffmpeg` for transcoding
- **Frontend**: Svelte 5 SPA with Tailwind CSS for the web interface
- **Deployment**: Multi-platform Docker support with deployment scripts

## Architecture

### Backend Structure (`backend/`)

- `media_grabber.py`: Core CLI and download logic
  - `download_and_extract_audio()`: Downloads and converts to MP3 using yt-dlp + ffmpeg
  - `download_video_file()`: Downloads and merges video+audio to MP4
  - `_prepare_download()`: Extracts metadata and sanitizes filenames (truncates to 50 chars, removes invalid chars)
- `media_grabber_web.py`: Flask REST API server
  - **Single Video Endpoints**: `/metadata`, `/download_start`, `/progress/<job_id>`, `/download_file/<job_id>`
  - **Playlist Endpoints**: `/playlist/metadata`, `/playlist/download_start`, `/playlist/progress/<job_id>`, `/playlist/download_file/<job_id>`
  - Job-based async download system using threading with `PROGRESS_STATE` and `PLAYLIST_STATE` dicts
  - Supports cookie authentication (JSON format from browser → Netscape format conversion)
  - 50MB size limit for Facebook/Instagram/Threads downloads
  - Playlist downloads: Sequential with configurable delay (default 3s) to avoid YouTube rate limiting
  - ZIP packaging for multiple MP3/MP4 files from playlists
- `test_media_grabber.py`: Unit tests using unittest and mocking
- `test_playlist.py`: Integration tests for playlist functionality (makes real network calls)

### Frontend Structure (`frontend/`)

- `src/App.svelte`: Main Svelte 5 component
  - Tab-based UI for different platforms (Instagram, YouTube, Facebook, Threads)
  - YouTube format selector (MP3/MP4)
  - **Playlist Detection**: Automatically detects YouTube playlist URLs (contains `list=` parameter)
  - **Playlist UI**: Video count, preview list, format selector, delay configuration
  - Metadata preview with thumbnail
  - Progress overlay with download stages (downloading → transcoding → completed)
  - **Playlist Progress**: Shows per-video and overall progress, failed videos list
  - Dark mode support with localStorage persistence
  - API communication via `fetch()` to Flask backend
- API base URL: `import.meta.env.VITE_API_BASE_URL` (defaults to `http://localhost:8080`)

### Configuration Files

- `pyproject.toml`: Python dependencies (Flask, yt-dlp, tqdm, Flask-CORS, gunicorn, ruff)
- `frontend/package.json`: Frontend dependencies (Svelte 5, Vite 6, Tailwind CSS, Sass)
- `frontend/vite.config.js`: Vite build configuration
- `Dockerfile`: Multi-stage build (Node.js → Python with ffmpeg)

## Development Workflows

### Running Backend (Development)

```bash
cd backend
uv sync                          # Install dependencies
uv run python media_grabber_web.py  # Start Flask on http://localhost:8080
```

Backend logs to console in development mode; uses gunicorn logger in production.

### Running Frontend (Development)

```bash
cd frontend
npm install                      # Install dependencies
npm run dev                      # Start Vite dev server on http://localhost:5173
```

Frontend uses `VITE_API_BASE_URL` environment variable to connect to backend.

### CLI Usage

```bash
cd backend
uv run python media_grabber.py <URL> [-f mp3|mp4] [-o OUTPUT_DIR] [-c COOKIE_FILE]
```

- Downloads to `../output` by default
- Requires `ffmpeg` in PATH

### Testing

#### Unit Tests (Mocked)

Run all unit tests:

```bash
cd backend
uv run python -m unittest test_media_grabber -v
```

Run specific test:

```bash
cd backend
uv run python -m unittest test_media_grabber.MediaGrabberTests.test_metadata_extraction_no_format_option -v
```

Tests use mocking to avoid actual network calls.

**Key Test Cases**:

- `test_metadata_extraction_no_format_option`: Verifies metadata extraction does NOT include `format` option (prevents "Requested format is not available" errors)
- `test_playlist_url_with_single_video`: Verifies `noplaylist=True` prevents full playlist extraction
- All other tests verify title sanitization, download options, and format specifications

#### Integration Tests (Real Network Calls)

Run integration tests with real YouTube URLs:

```bash
cd backend
uv run python test_integration.py
```

Run specific integration test:

```bash
cd backend
uv run python test_integration.py TestRealYouTubeMetadata.test_restricted_format_video
```

**Playlist Integration Tests**:

```bash
cd backend
uv run python test_playlist.py                              # All playlist tests
uv run python test_playlist.py TestPlaylistMetadata -v      # Metadata tests only
```

**Note**: Integration tests make actual network calls and may fail due to:

- Network connectivity issues
- YouTube anti-bot protection (HTTP 403)
- Rate limiting

See `backend/TEST_RESULTS.md` for detailed test results and analysis.
See `backend/PLAYLIST_DOWNLOAD_DESIGN.md` for playlist feature architecture.

### Building Frontend

```bash
cd frontend
npm run build                    # Output to frontend/dist/
```

## Docker Deployment

### Multi-Platform Build & Push

Use `scripts/deploy.sh` for production deployment:

```bash
cd scripts
./deploy.sh                      # Uses default API URL: https://media.brianhan.cc
./deploy.sh https://api.example.com  # Custom API URL
```

This script:

1. Creates/uses buildx builder for `linux/amd64` (arm64 commented out)
2. Passes `VITE_API_BASE_URL` as build arg to frontend
3. Builds and pushes to Docker Hub as `sacahan/media-grabber:latest`
4. Does NOT retain local image

### Container Management

```bash
docker stop mediagrabber && docker rm mediagrabber
```

## Key Dependencies

- **ffmpeg**: Required for audio/video transcoding (install via brew/apt/yum)
- **yt-dlp**: Core download library with format selection and post-processing
- **Flask + Flask-CORS**: Backend API with CORS support
- **Svelte 5**: Reactive frontend framework (uses new runes API)
- **Tailwind CSS**: Utility-first styling
- **gunicorn**: Production WSGI server (Note: Flask is WSGI, not ASGI, so async benefits are limited)

## Important Behaviors

### Cookie Handling

- Web UI sends JSON cookie array
- Backend converts to Netscape format in temp file
- CLI accepts cookie file path directly

### Download Flow

#### Single Video Download

1. Frontend calls `/metadata` to get title/thumbnail
2. User clicks download → `/download_start` creates job_id
3. Background thread runs download with progress hooks
4. Frontend polls `/progress/<job_id>` every 1s
5. When done, `/download_file/<job_id>` streams file and cleans up temp dir

#### Playlist Download Flow

1. Frontend detects playlist URL (contains `list=` parameter)
2. Calls `/playlist/metadata` to get playlist info (title, video count, video list)
3. Displays playlist UI with:
   - **Video selection checkboxes** (all selected by default)
   - **Select All / Deselect All** toggle button
   - Configuration options (format, delay)
   - Selected count display (e.g., "3 / 10")
4. User selects videos and clicks download → `/playlist/download_start` with `selected_videos` array
5. Backend filters videos and downloads only **selected videos sequentially** with configurable delay
6. Frontend polls `/playlist/progress/<job_id>` every 2s for:
   - Overall progress percentage
   - Current video being downloaded
   - Completed video count
   - Failed videos list
7. When all selected videos complete, backend creates ZIP file: `{playlist_title}_{timestamp}.zip`
8. Frontend auto-downloads ZIP via `/playlist/download_file/<job_id>`
9. Temporary files and ZIP cleaned up after download

### Filename Sanitization

- Removes invalid chars: `<>:"/\|?*`
- Truncates to 50 characters
- Applied to all downloaded files

### Size Limits

- Facebook/Instagram/Threads: 50MB limit (checked before download)
- YouTube (single video): No size limit
- YouTube (playlist): 50 video limit per request (configurable in code)

### Playlist-Specific Constraints

- **Rate Limiting**: Sequential downloads with configurable delay (default 3s, range 1-10s)
  - Prevents YouTube anti-bot protection (HTTP 403)
  - Recommended: Increase delay for large playlists (>20 videos)
- **Error Handling**: Failed videos don't stop the process
  - Failed videos tracked with error messages
  - Displayed to user after completion
- **ZIP File Naming**: `{sanitized_playlist_title}_{YYYYmmdd_HHMMSS}.zip`
- **Progress Tracking**: Both per-video and overall progress percentages
- **Cleanup**: All temporary MP3/MP4 files deleted after ZIP creation

## Code Quality

### Python Standards

- Use `uv` for all dependency management (not pip)
- Follow PEP 8: 4 spaces, snake_case, 180 char line limit
- Type hints for all functions
- Docstrings for public functions
- Use `ruff` for linting (configured via `.pre-commit-config.yaml`)

### Testing Standards

- Use unittest with mocking for external dependencies
- Test functions directly (import and test actual implementation)
- Do NOT reimplement logic in tests
- Mock only external dependencies (YoutubeDL, file I/O)

### Frontend Standards

- Use Svelte 5 runes (`$state`, `$derived`, `$effect`)
- Follow component-based architecture
- Tailwind for all styling (avoid custom CSS except animations)
- Use `onMount` for initialization
- Debounce API calls (500ms for URL input)

## Environment Variables

- `VITE_API_BASE_URL`: Frontend API base URL (build-time for Vite)
- `TK_SILENCE_DEPRECATION`: Set to `1` on macOS to suppress Tk warnings

## Scripts (`scripts/`)

- `deploy.sh`: Multi-platform Docker build and push with custom API URL support
- `startup.sh`: Service startup helper (customize as needed)

## Additional Notes

- Python version requirement: ≥3.8 (project uses 3.10 in Docker)
- Node.js: Use LTS version
- Frontend uses dark mode detection from `prefers-color-scheme`
- Backend uses threading (not asyncio) for concurrent downloads
- Temporary files cleaned up after download completes
- All API responses use JSON format
