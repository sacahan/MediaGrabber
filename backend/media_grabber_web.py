#!/usr/bin/env python3
"""
MediaGrabber Web GUI using Flask (YouTube MP3, Facebook/Instagram MP4).
"""

# This is a test comment for pre-commit validation.

from pathlib import Path
import tempfile
import shutil
import json
import os
from flask import (
    Flask,
    request,
    Response,
    stream_with_context,
    jsonify,
    send_from_directory,
)
from flask_cors import CORS  # Import Flask-CORS

from media_grabber import download_and_extract_audio, download_video_file

from urllib.parse import quote
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, GeoRestrictedError
import logging
from logging.handlers import RotatingFileHandler

import threading
import uuid
import time
import zipfile
from datetime import datetime

app = Flask(__name__, static_folder="frontend/dist", static_url_path="/")
CORS(app)

# Setup logging directory
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

if __name__ != "__main__":
    # When running via Gunicorn, it handles logging.
    # We can inherit Gunicorn's logger settings.
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    # Make sure that other loggers also use the gunicorn handler
    logging.basicConfig(
        handlers=gunicorn_logger.handlers, level=gunicorn_logger.level, force=True
    )
else:
    # When running directly for development, log to both console and file.
    # Create file handler with rotation (max 10MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOGS_DIR / "mediagrabber.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[file_handler, console_handler],
        force=True,
    )
    app.logger.setLevel(logging.INFO)

# Dictionary to store the progress and status of each download job.
# Key: job_id (string), Value: dictionary containing 'progress', 'status', 'stage', etc.
PROGRESS_STATE = {}

# Dictionary to store the progress and status of each playlist download job.
# Key: job_id (string), Value: dictionary containing playlist download state
PLAYLIST_STATE = {}


def _create_cookie_file(cookie: str | None, tmpdir: str) -> str | None:
    """Handles cookie logic. If cookie is JSON, converts to Netscape format
    and writes to a temp file inside tmpdir. Otherwise, assumes it's a file path.
    Returns the path to the cookie file if created/provided, else None.
    """
    if not cookie:
        logging.debug("No cookie provided")
        return None

    # Check if the cookie is in JSON format (from web UI)
    if cookie.strip().startswith("["):
        try:
            cookies_data = json.loads(cookie)
            logging.debug(
                f"Converting {len(cookies_data)} cookies from JSON format to Netscape format"
            )
            netscape_cookies = ["# Netscape HTTP Cookie File"]
            for c in cookies_data:
                domain = c.get("domain", "")
                host_only = c.get("hostOnly", False)

                # Netscape format: domain starting with dot = applies to subdomains (all_domains=TRUE)
                # domain without dot = applies only to exact host (all_domains=FALSE)
                # hostOnly=False means it's a domain cookie (should have leading dot)
                # hostOnly=True means it's host-specific (should NOT have leading dot)
                if host_only:
                    # Host-specific cookie: remove leading dot if present
                    if domain.startswith("."):
                        domain = domain[1:]
                    all_domains = "FALSE"
                else:
                    # Domain cookie: ensure leading dot
                    if not domain.startswith("."):
                        domain = "." + domain
                    all_domains = "TRUE"

                path = c.get("path", "/")
                secure = "TRUE" if c.get("secure", False) else "FALSE"
                expires = str(int(c.get("expirationDate", 0)))
                name = c.get("name", "")
                value = c.get("value", "")
                netscape_cookies.append(
                    f"{domain}\t{all_domains}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
                )

            cookie_file_path = os.path.join(tmpdir, "cookies.txt")
            with open(cookie_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(netscape_cookies))
            logging.info(f"Cookie file created at: {cookie_file_path}")
            return cookie_file_path
        except (json.JSONDecodeError, AttributeError) as e:
            # Not valid JSON, assume it's a file path from CLI
            logging.warning(
                f"Failed to parse cookies as JSON: {e}. Assuming it's a file path: {cookie}"
            )
            return cookie
    else:
        # Not JSON, assume it's a file path from CLI
        logging.debug(f"Cookie provided as file path: {cookie}")
        return cookie


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    """Serves the Svelte frontend's static files."""
    if path != "" and Path(app.static_folder, path).exists():
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")


@app.route("/metadata", methods=["POST"])
def get_metadata():
    """
    API endpoint to fetch video metadata (title, thumbnail) from a given URL.
    This is used by the frontend to display video information before download.
    """
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    cookie = data.get("cookie")
    if not url:
        logging.warning("Metadata request received without URL")
        return jsonify({"error": "The URL is required"}), 400

    logging.info(f"Fetching metadata for URL: {url}")
    tmpdir = tempfile.mkdtemp()
    cookie_file_path = _create_cookie_file(cookie, tmpdir)

    try:
        # For metadata extraction with download=False, do NOT specify format
        # This prevents yt-dlp from validating format availability
        # Reference: https://github.com/yt-dlp/yt-dlp official examples
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            # 添加現代的 User-Agent 避免被認定為機器人
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # HTTP 頭部用於繞過反爬蟲
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            },
            # 網絡優化
            "socket_timeout": 30,
            "skip_unavailable_fragments": True,
        }
        if cookie_file_path:
            ydl_opts["cookiefile"] = cookie_file_path

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get("title", "Unknown")
        thumbnail = info.get("thumbnail", "")
        logging.info(f"Metadata extracted successfully: title='{title}'")
        return jsonify({"title": title, "thumbnail": thumbnail})
    except (ExtractorError, DownloadError) as e:
        error_msg = str(e)
        logging.warning(f"Could not extract metadata for {url}: {error_msg}")

        # Special handling for Facebook "Cannot parse data" error
        if "facebook" in url.lower() and "Cannot parse data" in error_msg:
            return (
                jsonify(
                    {
                        "error": "無法解析 Facebook Reels 影片資料。這可能是因為：\n"
                        "1. Facebook 已更改網頁結構，yt-dlp 尚未支援\n"
                        "2. 該影片需要登入才能存取\n"
                        "3. 該影片受到地區限制\n\n"
                        "建議：請嘗試使用 Cookie 認證，或稍後再試。"
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "error": "Could not extract video information. The URL might be invalid or unsupported."
                }
            ),
            500,
        )
    except GeoRestrictedError as e:
        logging.warning(f"GeoRestricted error for {url}: {e}")
        return jsonify({"error": "Video is not available in your region."}), 500
    except Exception as e:
        logging.error(f"Error fetching metadata for {url}: {e}", exc_info=True)
        return (
            jsonify({"error": "An unexpected error occurred. Please try again."}),
            500,
        )
    finally:
        shutil.rmtree(tmpdir)


def do_download(
    job_id: str, url: str, source: str, format: str = "mp3", cookie: str = None
):
    """
    Background task to perform the actual media download and update its progress state.
    This function runs in a separate thread to avoid blocking the main Flask application.
    """
    tmpdir = tempfile.mkdtemp()
    state = PROGRESS_STATE.get(job_id, {})
    state["stage"] = "downloading"
    logging.info(
        f"[{job_id}] Starting download for {url} (source: {source}, format: {format})"
    )

    cookie_file_path = _create_cookie_file(cookie, tmpdir)

    def hook(d):
        """
        Progress hook for yt-dlp. This function is called by yt-dlp during the download process.
        It updates the global PROGRESS_STATE with current download progress and stage.
        """
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                state["progress"] = int(downloaded / total * 100)
        elif status == "finished":
            state["progress"] = 100
            state["stage"] = "transcoding"
            logging.info(
                f"[{job_id}] yt-dlp finished downloading. Starting post-processing."
            )

    try:
        # 構建通用的 yt-dlp 選項 (所有來源共用)
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            # 添加現代的 User-Agent 避免被認定為機器人
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # HTTP 頭部用於繞過反爬蟲
            "http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            },
            # 網絡優化
            "socket_timeout": 30,
            "skip_unavailable_fragments": True,
        }

        # 來源特定配置
        if source == "youtube":
            ydl_opts["http_headers"]["Referer"] = "https://www.youtube.com/"
        elif source == "twitter":
            ydl_opts["http_headers"]["Referer"] = "https://x.com/"
        elif source == "facebook":
            ydl_opts["http_headers"]["Referer"] = "https://www.facebook.com/"
        elif source == "instagram":
            ydl_opts["http_headers"]["Referer"] = "https://www.instagram.com/"
            ydl_opts["extractor_args"] = {"instagram": {"fetch_all_comments": False}}
        else:
            raise ValueError(f"Unsupported source: {source}")

        if cookie_file_path:
            ydl_opts["cookiefile"] = cookie_file_path

        # 提取元數據並檢查文件大小（視頻來源需要檢查）
        if source != "youtube" or format == "mp4":
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

            size = info_dict.get("filesize") or info_dict.get("filesize_approx", 0)
            # YouTube MP3 無大小限制，其他來源 50MB limit
            size_limit = (
                float("inf")
                if (source == "youtube" and format == "mp3")
                else 50 * 1024 * 1024
            )

            if size and size > size_limit:
                shutil.rmtree(tmpdir)
                logging.warning(
                    f"[{job_id}] Video size ({size} bytes) exceeds limit ({size_limit} bytes)."
                )
                state.update(status="error", error="Video size exceeds limit")
                return

        # YouTube 特殊處理：MP3 和 MP4 格式差異
        if source == "youtube":
            if format == "mp3":
                download_and_extract_audio(
                    url, Path(tmpdir), progress_hook=hook, cookiefile=cookie_file_path
                )
                pattern = "*.mp3"
                mimetype = "audio/mpeg"
            else:  # mp4
                download_video_file(
                    url, Path(tmpdir), progress_hook=hook, cookiefile=cookie_file_path
                )
                pattern = "*.mp4"
                mimetype = "video/mp4"

        # Twitter、Facebook、Instagram 使用相同邏輯
        else:
            download_video_file(
                url, Path(tmpdir), progress_hook=hook, cookiefile=cookie_file_path
            )
            pattern = "*.mp4"
            mimetype = "video/mp4"

        files = list(Path(tmpdir).glob(pattern))
        if not files:
            shutil.rmtree(tmpdir)
            logging.error(
                f"[{job_id}] Post-processing failed: {pattern} file not found."
            )
            state.update(status="error", error=f"{pattern} file not found")
            return

        file_path = files[0]
        logging.info(f"[{job_id}] Download successful. File is at {file_path}")
        state.update(
            status="done",
            stage="completed",
            file_path=str(file_path),
            tmpdir=tmpdir,
            filename=file_path.name,
            mimetype=mimetype,
        )
    except GeoRestrictedError as e:
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] Download failed: {e}")
        state.update(status="error", error="Video is not available in your region.")
    except ExtractorError as e:
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] Download failed: {e}")
        state.update(
            status="error",
            error="Could not extract video information. The URL might be invalid or unsupported.",
        )
    except DownloadError as e:
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] Download failed: {e}")
        state.update(status="error", error=f"Download failed: {e}")
    except Exception as e:
        shutil.rmtree(tmpdir)
        logging.error(f"[{job_id}] An unexpected error occurred: {e}", exc_info=True)
        state.update(
            status="error",
            error="An unexpected error occurred. Please check the server logs.",
        )


@app.route("/download_start", methods=["POST"])
def download_start():
    """
    API endpoint to initiate a download.
    It creates a new job_id and starts the do_download function in a separate thread.
    """
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "The URL is required"}), 400
    source = data.get("source", "youtube")
    format = data.get("format", "mp3")
    cookie = data.get("cookie")
    job_id = uuid.uuid4().hex  # Generate a unique ID for this download job.
    PROGRESS_STATE[job_id] = {"progress": 0, "status": "in_progress", "stage": "queued"}
    logging.info(f"[{job_id}] Queuing download for {url}")
    threading.Thread(
        target=do_download, args=(job_id, url, source, format, cookie), daemon=True
    ).start()
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>", methods=["GET"])
def download_progress(job_id):
    """
    API endpoint to get the current progress of a specific download job.
    Frontend polls this endpoint to update the progress bar and status messages.
    """
    state = PROGRESS_STATE.get(job_id)
    if not state:
        return jsonify({"error": "Job not found"}), 404
    resp = {
        "progress": state.get("progress", 0),
        "status": state.get("status"),
        "stage": state.get("stage", "unknown"),
    }
    if state.get("status") == "error":
        resp["error"] = state.get("error")
    return jsonify(resp)


@app.route("/download_file/<job_id>", methods=["GET"])
def download_file(job_id):
    """
    API endpoint to serve the downloaded file to the user.
    This streams the file content and cleans up the temporary directory afterwards.
    """
    logging.info(f"Download file request for job_id: {job_id}")
    state = PROGRESS_STATE.get(job_id)
    if not state or state.get("status") != "done" or not state.get("file_path"):
        logging.warning(f"File not ready for job_id: {job_id}. State: {state}")
        return jsonify({"error": "File not ready"}), 404
    file_path = state["file_path"]
    tmpdir = state["tmpdir"]
    filename = state["filename"]
    mimetype = state["mimetype"]

    logging.info(
        f"Serving file: {filename} (size: {Path(file_path).stat().st_size} bytes)"
    )

    def generate():
        """Generator function to stream the file in chunks."""
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
        logging.debug(f"File streaming completed for job_id: {job_id}")
        shutil.rmtree(tmpdir)
        PROGRESS_STATE.pop(job_id, None)
        logging.info(
            f"Cleaned up temporary directory and removed job state for job_id: {job_id}"
        )

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "Content-Length": str(Path(file_path).stat().st_size),
    }
    return Response(stream_with_context(generate()), mimetype=mimetype, headers=headers)


# ============================================================================
# Playlist Download Endpoints
# ============================================================================


@app.route("/playlist/metadata", methods=["POST"])
def get_playlist_metadata():
    """
    API endpoint to fetch playlist metadata.
    Returns playlist title, video count, and list of videos.
    """
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    cookie = data.get("cookie")

    if not url:
        logging.warning("Playlist metadata request received without URL")
        return jsonify({"error": "The URL is required"}), 400

    logging.info(f"Fetching playlist metadata for URL: {url}")
    tmpdir = tempfile.mkdtemp()
    cookie_file_path = _create_cookie_file(cookie, tmpdir)

    try:
        # Extract playlist information without downloading
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",  # Only extract playlist metadata
        }
        if cookie_file_path:
            ydl_opts["cookiefile"] = cookie_file_path

        with YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(url, download=False)

        # Check if it's actually a playlist
        if playlist_info.get("_type") != "playlist":
            logging.warning(f"URL is not a playlist: {url}")
            return (
                jsonify(
                    {
                        "error": "This URL is not a playlist. Use the regular download for single videos."
                    }
                ),
                400,
            )

        videos = playlist_info.get("entries", [])
        video_list = []
        for video in videos[:50]:  # Limit to first 50 videos
            if video:  # Some entries might be None
                video_list.append(
                    {
                        "id": video.get("id"),
                        "title": video.get("title", "Unknown"),
                        "duration": video.get("duration"),
                    }
                )

        playlist_title = playlist_info.get("title", "Unknown Playlist")
        logging.info(
            f"Playlist metadata fetched: title='{playlist_title}', videos={len(videos)}"
        )
        return jsonify(
            {
                "title": playlist_title,
                "uploader": playlist_info.get("uploader", "Unknown"),
                "video_count": len(videos),
                "videos": video_list,
            }
        )

    except (ExtractorError, DownloadError) as e:
        logging.warning(f"Could not extract playlist metadata for {url}: {e}")
        return (
            jsonify(
                {
                    "error": "Could not extract playlist information. The URL might be invalid."
                }
            ),
            500,
        )
    except Exception as e:
        logging.error(f"Error fetching playlist metadata for {url}: {e}", exc_info=True)
        return (
            jsonify({"error": "An unexpected error occurred. Please try again."}),
            500,
        )
    finally:
        shutil.rmtree(tmpdir)


def do_playlist_download(
    job_id: str,
    playlist_url: str,
    format: str = "mp3",
    delay: int = 3,
    cookie: str = None,
    max_videos: int = 50,
    selected_videos: list = None,
):
    """
    Background task to download selected videos in a playlist sequentially.
    Packs all downloaded files into a ZIP archive.

    Args:
        selected_videos: List of video IDs to download. If None, downloads all videos.
    """
    tmpdir = tempfile.mkdtemp()
    state = PLAYLIST_STATE.get(job_id, {})
    state["status"] = "in_progress"
    state["stage"] = "extracting_playlist"

    logging.info(f"[{job_id}] Starting playlist download for {playlist_url}")

    cookie_file_path = _create_cookie_file(cookie, tmpdir)

    try:
        # 1. Extract playlist information
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
        }
        if cookie_file_path:
            ydl_opts["cookiefile"] = cookie_file_path

        with YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)

        all_videos = playlist_info.get("entries", [])[:max_videos]  # Limit max videos

        # Filter videos based on selected_videos list
        if selected_videos:
            videos = [v for v in all_videos if v and v.get("id") in selected_videos]
            logging.info(
                f"[{job_id}] Filtered {len(videos)} selected videos from {len(all_videos)} total"
            )
        else:
            videos = all_videos

        state["total_videos"] = len(videos)
        state["completed_videos"] = 0
        state["failed_videos"] = []
        state["stage"] = "downloading"

        downloaded_files = []

        # 2. Download each selected video sequentially
        for i, video in enumerate(videos):
            if not video:  # Skip None entries
                continue

            state["current_video"] = {
                "index": i + 1,
                "title": video.get("title", "Unknown"),
                "progress": 0,
            }

            video_url = f"https://www.youtube.com/watch?v={video['id']}"
            logging.info(
                f"[{job_id}] Downloading video {i+1}/{len(videos)}: {video.get('title')}"
            )

            def hook(d):
                """Progress hook for individual video download"""
                status = d.get("status")
                if status == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    if total:
                        state["current_video"]["progress"] = int(
                            downloaded / total * 100
                        )
                elif status == "finished":
                    state["current_video"]["progress"] = 100

            try:
                # Download video as MP3
                if format == "mp3":
                    download_and_extract_audio(
                        video_url,
                        Path(tmpdir),
                        progress_hook=hook,
                        cookiefile=cookie_file_path,
                    )
                    pattern = "*.mp3"
                else:
                    download_video_file(
                        video_url,
                        Path(tmpdir),
                        progress_hook=hook,
                        cookiefile=cookie_file_path,
                    )
                    pattern = "*.mp4"

                # Find the downloaded file
                files = list(Path(tmpdir).glob(pattern))
                if files:
                    # Get the most recently modified file
                    latest_file = max(files, key=lambda p: p.stat().st_mtime)
                    downloaded_files.append(latest_file)
                    state["completed_videos"] = i + 1
                    logging.info(
                        f"[{job_id}] Successfully downloaded: {latest_file.name}"
                    )

                # Add delay between downloads to avoid rate limiting
                if i < len(videos) - 1:  # Don't delay after last video
                    time.sleep(delay)

            except Exception as e:
                logging.error(
                    f"[{job_id}] Failed to download video {i+1}: {e}", exc_info=True
                )
                state["failed_videos"].append(
                    {
                        "index": i + 1,
                        "title": video.get("title", "Unknown"),
                        "error": str(e),
                    }
                )

        # 3. Pack all downloaded files into a ZIP
        if not downloaded_files:
            state.update(status="error", error="No videos were successfully downloaded")
            shutil.rmtree(tmpdir)
            return

        state["stage"] = "packing"
        playlist_title = playlist_info.get("title", "playlist")
        # Sanitize playlist title for filename
        import re

        safe_title = re.sub(r'[<>:"/\\|?*]', "_", playlist_title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{safe_title}_{timestamp}.zip"
        zip_path = Path(tmpdir) / zip_filename

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in downloaded_files:
                zipf.write(file_path, file_path.name)

        logging.info(
            f"[{job_id}] Playlist download complete. ZIP created: {zip_filename}"
        )

        # 4. Update state
        state.update(
            {
                "status": "completed",
                "stage": "completed",
                "zip_path": str(zip_path),
                "zip_filename": zip_filename,
                "tmpdir": tmpdir,
            }
        )

    except Exception as e:
        logging.error(f"[{job_id}] Playlist download failed: {e}", exc_info=True)
        state.update(status="error", error=f"Playlist download failed: {e}")
        shutil.rmtree(tmpdir)


@app.route("/playlist/download_start", methods=["POST"])
def playlist_download_start():
    """
    API endpoint to start a playlist download.
    Downloads selected videos (or all if none specified) sequentially and packs them into a ZIP file.
    """
    data = request.get_json() or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "The URL is required"}), 400

    format = data.get("format", "mp3")
    delay = data.get("delay", 3)  # Default 3 seconds delay
    cookie = data.get("cookie")
    max_videos = data.get("max_videos", 50)  # Default max 50 videos
    selected_videos = data.get("selected_videos")  # List of selected video IDs

    # Validate selected_videos
    if selected_videos is not None and not isinstance(selected_videos, list):
        return jsonify({"error": "selected_videos must be a list"}), 400

    if selected_videos is not None and len(selected_videos) == 0:
        return jsonify({"error": "At least one video must be selected"}), 400

    job_id = uuid.uuid4().hex
    PLAYLIST_STATE[job_id] = {
        "progress": 0,
        "status": "in_progress",
        "stage": "queued",
        "total_videos": 0,
        "completed_videos": 0,
        "failed_videos": [],
    }

    selected_count = len(selected_videos) if selected_videos else "all"
    logging.info(
        f"[{job_id}] Queuing playlist download for {url} ({selected_count} videos)"
    )

    threading.Thread(
        target=do_playlist_download,
        args=(job_id, url, format, delay, cookie, max_videos, selected_videos),
        daemon=True,
    ).start()

    return jsonify({"job_id": job_id})


@app.route("/playlist/progress/<job_id>", methods=["GET"])
def playlist_progress(job_id):
    """
    API endpoint to get the current progress of a playlist download job.
    """
    state = PLAYLIST_STATE.get(job_id)
    if not state:
        return jsonify({"error": "Job not found"}), 404

    resp = {
        "status": state.get("status"),
        "stage": state.get("stage"),
        "total_videos": state.get("total_videos", 0),
        "completed_videos": state.get("completed_videos", 0),
        "failed_videos": state.get("failed_videos", []),
    }

    # Include current video progress if available
    current_video = state.get("current_video")
    if current_video:
        resp["current_video"] = current_video

    # Calculate overall progress
    total = state.get("total_videos", 0)
    completed = state.get("completed_videos", 0)
    if total > 0:
        resp["overall_progress"] = int((completed / total) * 100)
    else:
        resp["overall_progress"] = 0

    if state.get("status") == "error":
        resp["error"] = state.get("error")

    return jsonify(resp)


@app.route("/playlist/download_file/<job_id>", methods=["GET"])
def playlist_download_file(job_id):
    """
    API endpoint to download the ZIP file containing all playlist videos.
    """
    logging.info(f"Playlist download file request for job_id: {job_id}")
    state = PLAYLIST_STATE.get(job_id)
    if not state or state.get("status") != "completed" or not state.get("zip_path"):
        logging.warning(
            f"Playlist ZIP file not ready for job_id: {job_id}. State: {state}"
        )
        return jsonify({"error": "File not ready"}), 404

    zip_path = state["zip_path"]
    zip_filename = state["zip_filename"]
    tmpdir = state["tmpdir"]

    file_size = Path(zip_path).stat().st_size
    logging.info(f"Serving playlist ZIP: {zip_filename} (size: {file_size} bytes)")

    def generate():
        """Generator function to stream the ZIP file"""
        with open(zip_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
        logging.debug(f"ZIP file streaming completed for job_id: {job_id}")
        # Cleanup after download
        shutil.rmtree(tmpdir)
        PLAYLIST_STATE.pop(job_id, None)
        logging.info(
            f"Cleaned up temporary directory and removed job state for job_id: {job_id}"
        )

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(zip_filename)}",
        "Content-Length": str(file_size),
    }

    return Response(
        stream_with_context(generate()), mimetype="application/zip", headers=headers
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080, use_reloader=False)
