# MediaGrabber

A simple Python downloader:

- **YouTube → MP3/MP4** via CLI or Web GUI (choose format)
- **Facebook → MP4** and **Instagram → MP4** via Web GUI (50 MB size limit)

![demo](https://github.com/user-attachments/assets/99ef6eaf-a6a2-43ef-b922-67d481daf400)

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

#### 3. CLI Usage

Download audio or video from supported platforms via script:

```bash
cd backend
source .venv/bin/activate # Activate virtual environment
python media_grabber.py <URL> [-f FORMAT] [-o OUTPUT_DIR]
```

Options:

- `-f, --format`: `mp3` (audio) or `mp4` (video). Default: `mp3`.
- `-o, --output`: Output directory (default: `../output`).

Examples:

- Download YouTube audio as MP3 to the project's root output directory

```bash
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp3 -o ../output
```

- Download YouTube video as MP4 to a custom directory

```bash
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp4 -o /path/to/your/videos
```

- Download Facebook video as MP4

```bash
cd backend
source .venv/bin/activate
python media_grabber.py https://facebook.com/... -f mp4
```

## Development

### Requirements

- Python 3.7 or newer
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
