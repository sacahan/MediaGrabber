# MediaGrabber

A simple Python downloader:

- **YouTube → MP3/MP4** via CLI or Web GUI (choose format)
- **Facebook → MP4** and **Instagram → MP4** via Web GUI (50 MB size limit)

![demo](https://github.com/user-attachments/assets/99ef6eaf-a6a2-43ef-b922-67d481daf400)

## Usage

This project can be run in two modes: **Docker** for a production-like containerized environment, and **Development** for local development and testing.

### Docker Mode

The `build_and_run.sh` script provides a convenient way to build and run the application using Docker. This is the recommended approach for a production-like environment.

#### Build and Run

Execute the script from the project root:

```bash
./build_and_run.sh
```

You can optionally pass a frontend API base URL when invoking the script, or set the `VITE_API_BASE_URL` environment variable. The value will be embedded into the frontend at build time so the produced SPA uses the correct backend endpoint.

Examples:

```bash
# use default (http://localhost:8080)
./build_and_run.sh

# pass custom API base URL as first argument
./build_and_run.sh https://api.example.com

# or via environment variable
VITE_API_BASE_URL=https://api.example.com ./build_and_run.sh
```

Notes:

- The script supports `-h` / `--help` to show usage information:

```bash
./build_and_run.sh -h
```

- The `Dockerfile` frontend build stage accepts a build-arg named `VITE_API_BASE_URL` (default: `http://localhost:8080`). The `build_and_run.sh` forwards the provided value to `docker build --build-arg VITE_API_BASE_URL=...`.

This script will:

1. Build the frontend and embed `VITE_API_BASE_URL` into the build.
2. Build a Docker image named `mediagrabber`.
3. Run a Docker container, mapping port `8080` to the host and mounting the `output` directory for persistent storage of downloaded files.

The application will be accessible at `http://localhost:8080`.

#### Stop and Remove

To stop and remove the Docker container, use the following command:

```bash
docker stop mediagrabber && docker rm mediagrabber
```

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

### Pre-commit Setup

This project uses `pre-commit` to automatically format and lint code before each commit, ensuring consistent code style.

After completing the backend and frontend installations, run the following command once from the project root to set up the Git hooks:

```bash
pre-commit install
```

Now, every time you run `git commit`, `pre-commit` will automatically run `Ruff` (for Python) and `Prettier` (for frontend files) to format your code. If any files are modified by the hooks, the commit will be aborted. Simply review the changes, `git add` the modified files, and commit again.
