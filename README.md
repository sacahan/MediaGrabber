# MediaGrabber

A simple Python downloader:
- **YouTube → MP3** via CLI or Web GUI
- **Facebook → MP4** and **Instagram → MP4** via Web GUI (50 MB size limit)

## Requirements

- Python 3.7 or newer
- `ffmpeg` installed and available in PATH
- On macOS, to suppress Tk deprecation warning set:
  ```bash
  export TK_SILENCE_DEPRECATION=1
  ```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# upgrade pip and wheel for best compatibility
pip install --upgrade pip wheel
# install dependencies
pip install -r requirements.txt
```

On macOS, install `ffmpeg` via Homebrew:

```bash
brew install ffmpeg
```

## Usage (CLI)

Download audio or video from supported platforms via script:

```bash
python media_grabber.py <URL> [-f FORMAT] [-o OUTPUT_DIR]
```

Options:
- `-f, --format`: `mp3` (audio) or `mp4` (video). Default: `mp3`.
- `-o, --output`: Output directory (default: `./output`).

Examples:

# Download YouTube audio as MP3
python media_grabber.py https://youtu.be/abc123 -f mp3 -o out_audio

# Download Facebook video as MP4
python media_grabber.py https://facebook.com/... -f mp4 -o out_video


## Web GUI Usage

A web-based interface with tabbed support for YouTube, Facebook and Instagram:

Ensure dependencies are installed (see Installation):

```bash
pip install -r requirements.txt
```

Run the server:

```bash
python media_grabber_web.py
```

Open http://localhost:8080 in your browser. Select one of the tabs:

- **YouTube**: extract MP3 audio from a YouTube URL
- **Facebook**: download MP4 video from a Facebook URL (max. 50 MB)
- **Instagram**: download MP4 video from an Instagram URL (max. 50 MB)

Paste your URL in the input box and click **Download**. The requested file will be streamed back automatically.