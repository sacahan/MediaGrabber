# MediaGrabber

A simple Python downloader:

- **YouTube → MP3/MP4** via CLI or Web GUI (choose format, playlist support)
- **Facebook → MP4** and **Instagram → MP4** via Web GUI (50 MB size limit)
- **X/Twitter → MP4** via Web GUI (no size limit)

![demo](https://github.com/user-attachments/assets/99ef6eaf-a6a2-43ef-b922-67d481daf400)

> **Interface parity**: Both the CLI (`python -m app.cli.main ...`) and REST API (`/api/downloads*`) now call the same download/transcode services, so every platform/format combination listed above is available from either entry point. Tests enforce that the CLI progress logs and REST `/progress` payloads expose identical fields (`status`, `stage`, `percent`, `queueDepth`, `remediation`).

## Usage

This project can be run in two modes: **Docker** for a production-like containerized environment, and **Development** for local development and testing.

### Docker Mode

This project supports multi-platform Docker build and push. For production-like deployment, it is recommended to use `scripts/deploy.sh`.

#### Multi-platform Build & Push

Run `scripts/deploy.sh` to:

1. Create/use a buildx builder for multi-platform support (`linux/amd64, linux/arm64`).
2. Pass API base url to frontend build via `--build-arg VITE_API_BASE_URL=...` (default: `https://media.brianhan.cc`, customizable).
3. Build and push the image to Docker Hub (no local image retained).

Example:

```bash
cd scripts
./deploy.sh # use default API base url
./deploy.sh https://api.example.com # specify API base url
```

`deploy.sh` automatically passes `VITE_API_BASE_URL` as a build-arg to Docker build, ensuring the frontend SPA connects to the correct endpoint.

After push, the image will be available at `sacahan/media-grabber:latest` on Docker Hub.

#### Stop and Remove Container

```bash
docker stop mediagrabber && docker rm mediagrabber
```

---

#### Notes

- `scripts/deploy.sh` is mainly for multi-platform build and push. For local testing, use `build_and_run.sh`.
- To customize buildx builder name, platforms, or other parameters, edit `deploy.sh` directly.

### Scripts

The project includes a `scripts/` directory:

- `deploy.sh`: Multi-platform Docker build and push, supports build-arg for API base url.
- `startup.sh`: For service startup or environment initialization (customize as needed).

It is recommended to use scripts in this directory for all deployment and build operations.

### Development Mode

In Development Mode, the frontend and backend are run as separate processes, allowing for hot-reloading and easier debugging.

#### Environment configuration (CLI + REST)

1. Duplicate `.env.example` to `.env` in the repository root.
1. Adjust the following knobs according to your workstation:

   - `MG_MAX_TRANSCODE_WORKERS`: Maximum concurrent ffmpeg jobs (default `2`).
   - `MG_OUTPUT_DIR`: Artifact root for both CLI + REST jobs (default `output`).
   - `MG_PROGRESS_TTL_SECONDS`: How long progress snapshots stay available for polling (default `300`).

1. Restart the Flask server _and_ relaunch any CLI sessions after editing `.env` so both entry points share the same settings.

> Tip: Because CLI 和 REST 共用同一個 service layer，請保持 `.env` 中的 MG\_\* 變數一致，以免兩種入口對輸出目錄或佇列限制有不同理解。

#### 1. Backend API (Flask)

Navigate to the `backend` directory and run the Flask application:

```bash
cd backend
python media_grabber_web.py
```

The Flask API will be running on `http://localhost:8080`. API logs will be saved in `backend/log/flask.log`.
**Note:** While Uvicorn is an ASGI server that provides better performance and asynchronous support for ASGI-compatible frameworks, Flask itself is a WSGI application and does not natively benefit from Uvicorn's async features. Uvicorn is used here primarily as a performant server, but true async support would require an ASGI framework like FastAPI or Starlette.

#### 2. Frontend (Svelte with Tailwind CSS)

Navigate to the `frontend` directory and start the Svelte development server:

```bash
cd frontend
npm run dev
```

The Svelte application will typically be running on `http://localhost:5173` (or another available port). Open this URL in your browser to use the Web GUI.

#### Web UI Features (T027)

The Web UI provides real-time progress tracking and unified access to all download platforms:

**Supported Platforms & Formats**:

- YouTube: MP3 (audio), MP4 (video)
- Instagram: MP4 (mobile-optimized)
- Facebook: MP4 (mobile-optimized)
- X (Twitter): MP4 (mobile-optimized)

**Progress Dashboard**:

- Real-time percent completion, ETA, and download speed
- Queue depth and position when multiple jobs are active
- Retry countdown and remaining attempts (when enabled)
- Remediation suggestions for common failures (e.g., ffmpeg missing, platform throttling)

**Platform-Restricted Content (Cookies)**:

For age-restricted or geo-locked videos, paste your browser cookies (as JSON) into the Cookies field:

1. Open the platform in your browser
2. Open DevTools → Storage → Cookies
3. Export as JSON (using browser extension or manual copy)
4. Paste into the "Cookies" field in MediaGrabber Web UI
5. Submit download

The UI will securely encode and transmit cookies to the backend for authentication.

#### 3. CLI Usage

Download audio or video from supported platforms using the new unified CLI:

```bash
# YouTube video
python -m app.cli.main download --url https://youtu.be/abc123 --format mp4

# YouTube playlist (creates ZIP with all videos)
python -m app.cli.main playlist --url https://youtube.com/playlist?list=... --format mp3

# Check job status
python -m app.cli.main status --job-id <JOB_ID>

# Retry failed job with backoff
python -m app.cli.main retry --job-id <JOB_ID>
```

The CLI shares the same backend services as the Web UI, so platform/format support and progress behavior are identical.

## Known Issues

### Facebook Reels - "Cannot parse data" Error

**Issue**: Some Facebook Reels videos may fail to download with error "Cannot parse data".

**Cause**: Facebook frequently changes its website structure, which can break yt-dlp's video extraction. This is an ongoing issue with yt-dlp's Facebook extractor.

**Solutions**:

1. **Use Cookie Authentication**: Export your Facebook cookies and upload them in the web UI

   - Use browser extension like "Get cookies.txt LOCALLY" (Chrome/Firefox)
   - Export cookies in JSON format
   - Upload in MediaGrabber's cookie field

2. **Update yt-dlp**: We're using the latest nightly build (2025.10.01), but Facebook issues may require waiting for yt-dlp updates

3. **Alternative**: Try downloading the video directly from Facebook's CDN (requires manual inspection of network requests)

**Related Issues**:

- yt-dlp GitHub: [#7901](https://github.com/yt-dlp/yt-dlp/issues/7901), [#8145](https://github.com/yt-dlp/yt-dlp/issues/8145)

**Note**: Regular Facebook videos (non-Reels) may work better. This issue primarily affects Facebook Reels format.

## Development

### Requirements

- Python 3.9 or newer (required by latest yt-dlp)
- Node.js (LTS recommended) and npm
- `ffmpeg` installed and available in PATH
- On macOS, to suppress Tk deprecation warning set:

  ```bash
  export TK_SILENCE_DEPRECATION=1
  ```

### Project Structure

```txt
MediaGrabber/
├── backend/             # Flask REST API and Python core logic
│   ├── media_grabber.py
│   ├── media_grabber_web.py
│   ├── pyproject.toml   # Python dependencies configuration
│   ├── .venv/           # Python virtual environment
│   ├── __pycache__/
│   └── log/             # Flask application logs
├── frontend/            # Svelte Single Page Application (SPA) with Tailwind CSS
│   ├── node_modules/
│   ├── public/
│   ├── src/
│   ├── .gitignore
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── svelte.config.js
│   ├── tailwind.config.js # Tailwind CSS configuration
│   └── vite.config.js
├── output/              # Default directory for downloaded media files
├── scripts/             # 部署與啟動相關腳本 (deploy.sh, startup.sh)
├── .gitignore
├── LICENSE
└── README.md
```

### Backend Installation

Navigate to the `backend` directory and install Python dependencies using `uv` (a modern Python dependency management tool):
Navigate to the `backend` directory and install Python dependencies using `uv`:

```bash
cd backend
# Install uv if not already installed
pip install uv

# Automatically create a virtual environment and install dependencies
uv sync
cd .. # Go back to project root
```

### Frontend Installation

Navigate to the `frontend` directory and install Node.js dependencies:

```bash
cd frontend
npm install
cd .. # Go back to project root
```

### FFmpeg Installation

On macOS, install `ffmpeg` via Homebrew:

```bash
brew install ffmpeg
```

On Windows, install `ffmpeg` via:

- **Chocolatey**: `choco install ffmpeg`
- **Scoop**: `scoop install ffmpeg`
- **Manual**: Download from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows) and add to PATH

On Linux (Ubuntu/Debian), install `ffmpeg` via:

```bash
sudo apt update
sudo apt install ffmpeg
```

On Linux (CentOS/RHEL/Fedora), install `ffmpeg` via:

```bash
# CentOS/RHEL
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```
