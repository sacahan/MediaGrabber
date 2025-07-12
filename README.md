# MediaGrabber

A simple Python downloader:
- **YouTube → MP3/MP4** via CLI or Web GUI (choose format)
- **Facebook → MP4** and **Instagram → MP4** via Web GUI (50 MB size limit)

## Project Structure

```
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

## Requirements

- Python 3.7 or newer
- Node.js (LTS recommended) and npm
- `ffmpeg` installed and available in PATH
- On macOS, to suppress Tk deprecation warning set:
  ```bash
  export TK_SILENCE_DEPRECATION=1
  ```

## Installation

### Backend Installation

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

## Development

This project uses `pre-commit` to automatically format and lint code before each commit, ensuring consistent code style.

### Pre-commit Setup

After completing the backend and frontend installations, run the following command once from the project root to set up the Git hooks:

```bash
pre-commit install
```

Now, every time you run `git commit`, `pre-commit` will automatically run `Ruff` (for Python) and `Prettier` (for frontend files) to format your code. If any files are modified by the hooks, the commit will be aborted. Simply review the changes, `git add` the modified files, and commit again.

## Usage

This project can be run in two modes: **Development** for local development and testing, and **Docker** for a production-like containerized environment.

### Development Mode

In Development Mode, the frontend and backend are run as separate processes, allowing for hot-reloading and easier debugging.

#### 1. Backend API (Flask with Uvicorn)

Navigate to the `backend` directory and run the Flask application using Uvicorn:

```bash
cd backend
python media_grabber_web.py
```

The Flask API will be running on `http://localhost:8080`. API logs will be saved in `backend/log/flask.log`. This approach uses Uvicorn for better performance and asynchronous support.

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

```
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp3 -o ../output
```

- Download YouTube video as MP4 to a custom directory

```
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp4 -o /path/to/your/videos
```

- Download Facebook video as MP4

```
cd backend
source .venv/bin/activate
python media_grabber.py https://facebook.com/... -f mp4
```

### Docker Mode

The `build_and_run.sh` script provides a convenient way to build and run the application using Docker. This is the recommended approach for a production-like environment.

#### Build and Run

Execute the script from the project root:

```bash
./build_and_run.sh
```

This script will:
1.  Build the frontend and copy the static files to the `backend/static` directory.
2.  Build a Docker image named `mediagrabber`.
3.  Run a Docker container, mapping port `8080` to the host and mounting the `output` directory for persistent storage of downloaded files.

The application will be accessible at `http://localhost:8080`.

#### Stop and Remove

To stop and remove the Docker container, use the following command:

```bash
docker stop mediagrabber && docker rm mediagrabber
```
