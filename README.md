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
│   ├── requirements.txt
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

Navigate to the `backend` directory and install Python dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# upgrade pip and wheel for best compatibility
pip install --upgrade pip wheel
# install dependencies
pip install -r requirements.txt
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

## Usage

### Backend API (Flask)

Navigate to the `backend` directory and run the Flask application:

```bash
cd backend
source .venv/bin/activate # Activate virtual environment
python media_grabber_web.py
```

The Flask API will be running on `http://localhost:8080`. API logs will be saved in `backend/log/flask.log`.

### Frontend (Svelte with Tailwind CSS)

Navigate to the `frontend` directory and start the Svelte development server:

```bash
cd frontend
npm run dev
```

The Svelte application will typically be running on `http://localhost:5173` (or another available port). Open this URL in your browser to use the Web GUI. The platform buttons (YouTube, Facebook, Instagram) now include icons for better visual identification.

### CLI Usage

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

# Download YouTube audio as MP3 to the project's root output directory
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp3 -o ../output

# Download YouTube video as MP4 to a custom directory
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp4 -o /path/to/your/videos

# Download Facebook video as MP4
cd backend
source .venv/bin/activate
python media_grabber.py https://facebook.com/... -f mp4
