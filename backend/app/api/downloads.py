"""Flask blueprint for downloads API with actual yt-dlp integration."""

from __future__ import annotations

import atexit
import logging
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request, send_file

# Configure module logger
logger = logging.getLogger(__name__)

downloads_bp = Blueprint("downloads", __name__)

# In-memory job store (production would use DB)
_jobs: dict = {}
_jobs_lock = threading.Lock()

# Output directory for downloads
OUTPUT_DIR = Path(os.environ.get("MG_OUTPUT_DIR", "output")).expanduser().resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Cleanup configuration
CLEANUP_INTERVAL_SECONDS = int(os.environ.get("MG_CLEANUP_INTERVAL", "3600"))  # 1 hour
FILE_MAX_AGE_SECONDS = int(os.environ.get("MG_FILE_MAX_AGE", "86400"))  # 24 hours
_cleanup_thread: Optional[threading.Thread] = None
_cleanup_stop_event = threading.Event()


def _cleanup_old_files() -> None:
    """Remove downloaded files older than FILE_MAX_AGE_SECONDS."""
    while not _cleanup_stop_event.is_set():
        try:
            logger.info("Starting cleanup of old download files...")
            now = time.time()
            cleaned_count = 0
            cleaned_size = 0

            # Iterate through job directories in output
            for job_dir in OUTPUT_DIR.iterdir():
                if not job_dir.is_dir():
                    continue

                # Check directory age by looking at modification time
                try:
                    dir_mtime = job_dir.stat().st_mtime
                    age_seconds = now - dir_mtime

                    if age_seconds > FILE_MAX_AGE_SECONDS:
                        # Calculate size before removal
                        dir_size = sum(
                            f.stat().st_size for f in job_dir.rglob("*") if f.is_file()
                        )

                        # Remove the directory
                        shutil.rmtree(job_dir)
                        cleaned_count += 1
                        cleaned_size += dir_size

                        # Also remove from jobs dict
                        job_id = job_dir.name
                        with _jobs_lock:
                            if job_id in _jobs:
                                del _jobs[job_id]

                        logger.debug(
                            f"Cleaned up job directory: {job_dir} "
                            f"(age: {age_seconds / 3600:.1f}h, size: {dir_size / 1024 / 1024:.2f}MB)"
                        )
                except Exception as e:
                    logger.warning(f"Error cleaning directory {job_dir}: {e}")

            if cleaned_count > 0:
                logger.info(
                    f"Cleanup completed: removed {cleaned_count} directories, "
                    f"freed {cleaned_size / 1024 / 1024:.2f}MB"
                )
            else:
                logger.debug("Cleanup completed: no old files to remove")

        except Exception as e:
            logger.error(f"Cleanup error: {e}", exc_info=True)

        # Wait for next cleanup interval
        _cleanup_stop_event.wait(CLEANUP_INTERVAL_SECONDS)


def start_cleanup_thread() -> None:
    """Start the background cleanup thread."""
    global _cleanup_thread
    if _cleanup_thread is None or not _cleanup_thread.is_alive():
        _cleanup_stop_event.clear()
        _cleanup_thread = threading.Thread(
            target=_cleanup_old_files, daemon=True, name="file-cleanup"
        )
        _cleanup_thread.start()
        logger.info(
            f"Started cleanup thread (interval: {CLEANUP_INTERVAL_SECONDS}s, "
            f"max age: {FILE_MAX_AGE_SECONDS}s)"
        )


def stop_cleanup_thread() -> None:
    """Stop the background cleanup thread."""
    global _cleanup_thread
    if _cleanup_thread and _cleanup_thread.is_alive():
        _cleanup_stop_event.set()
        _cleanup_thread.join(timeout=5)
        logger.info("Cleanup thread stopped")
    _cleanup_thread = None


# Start cleanup thread when module loads
start_cleanup_thread()

# Register cleanup on exit
atexit.register(stop_cleanup_thread)


def _get_platform(url: str) -> Optional[str]:
    """Determine platform from URL."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if "youtube.com" in netloc or "youtu.be" in netloc:
            return "youtube"
        elif "instagram.com" in netloc:
            return "instagram"
        elif "facebook.com" in netloc:
            return "facebook"
        elif "x.com" in netloc or "twitter.com" in netloc:
            return "x"
        return None
    except Exception:
        return None


def _is_valid_url(url: str) -> bool:
    """Validate URL format and supported platforms."""
    return _get_platform(url) is not None


def _is_valid_format(fmt: str) -> bool:
    """Validate format parameter."""
    return fmt in ["mp4", "mp3"]


def _update_job(job_id: str, **kwargs) -> None:
    """Thread-safe job update."""
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)
            logger.debug(f"[{job_id}] Job updated: {kwargs}")


def _run_download(
    job_id: str, url: str, fmt: str, cookies_path: Optional[Path] = None
) -> None:
    """Execute download in background thread using yt-dlp."""
    logger.info(f"[{job_id}] Starting download: url={url}, format={fmt}")

    try:
        from yt_dlp import YoutubeDL

        _update_job(
            job_id,
            status="downloading",
            stage="initializing",
            percent=5,
            message="初始化下載...",
        )

        # Create job-specific output directory
        job_output_dir = OUTPUT_DIR / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"[{job_id}] Output directory: {job_output_dir}")

        # Configure yt-dlp options
        ydl_opts = {
            "outtmpl": str(job_output_dir / "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "progress_hooks": [lambda d: _progress_hook(job_id, d)],
            "keepvideo": False,  # Remove intermediate files after merging
        }

        # Format-specific options
        if fmt == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
            logger.debug(f"[{job_id}] Configured for MP3 extraction")
        else:
            # MP4 video download - download best video and audio and merge
            # Format selection: prefer combining separate video+audio streams for better quality
            # bv*+ba: best video + best audio (any codec)
            # b: fallback to single file with both video and audio
            # Explicitly exclude audio-only formats
            ydl_opts["format"] = "(bv*[ext=mp4]+ba[ext=m4a]/bv*+ba)/b[height>=360]/b"
            ydl_opts["merge_output_format"] = "mp4"
            # Ensure ffmpeg is available for merging
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4",
                }
            ]
            logger.debug(f"[{job_id}] Configured for MP4 video download with merge")

        # Add cookies if provided
        if cookies_path and cookies_path.exists():
            ydl_opts["cookiefile"] = str(cookies_path)
            logger.info(f"[{job_id}] Using cookies from: {cookies_path}")

        # Platform-specific options
        platform = _get_platform(url)
        if platform == "instagram":
            # Instagram often needs cookies for best results
            instagram_cookies = (
                Path(__file__).parent.parent.parent / "cookies" / "instagram.txt"
            )
            if instagram_cookies.exists():
                ydl_opts["cookiefile"] = str(instagram_cookies)
                logger.info(f"[{job_id}] Using Instagram cookies: {instagram_cookies}")

        logger.info(f"[{job_id}] yt-dlp options configured, starting download...")
        _update_job(job_id, stage="downloading", percent=10, message="正在下載...")

        # Execute download
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if info is None:
                raise Exception("Failed to extract video info")

            title = info.get("title", "unknown")
            logger.info(f"[{job_id}] Download completed: {title}")

            # Find the downloaded file
            downloaded_file = None
            for f in job_output_dir.iterdir():
                if f.is_file():
                    downloaded_file = f
                    break

            if downloaded_file:
                file_size = downloaded_file.stat().st_size
                logger.info(
                    f"[{job_id}] File saved: {downloaded_file} ({file_size} bytes)"
                )

                _update_job(
                    job_id,
                    status="completed",
                    stage="completed",
                    percent=100,
                    message="下載完成！",
                    title=title,
                    filePath=str(downloaded_file),
                    fileSize=file_size,
                    downloadUrl=f"/api/downloads/{job_id}/file",
                )
            else:
                raise Exception("Downloaded file not found")

    except ImportError as e:
        logger.error(f"[{job_id}] yt-dlp not installed: {e}")
        _update_job(
            job_id,
            status="failed",
            stage="error",
            percent=0,
            message="yt-dlp 未安裝",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"[{job_id}] Download failed: {e}", exc_info=True)
        _update_job(
            job_id,
            status="failed",
            stage="error",
            percent=0,
            message=f"下載失敗: {str(e)}",
            error=str(e),
        )


def _progress_hook(job_id: str, d: dict) -> None:
    """yt-dlp progress callback."""
    status = d.get("status")

    if status == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        downloaded = d.get("downloaded_bytes", 0)
        speed = d.get("speed", 0)
        eta = d.get("eta", -1)

        if total > 0:
            percent = min(95, int((downloaded / total) * 100))
        else:
            percent = 50  # Unknown total

        _update_job(
            job_id,
            status="downloading",
            stage="downloading",
            percent=percent,
            downloadedBytes=downloaded,
            totalBytes=total,
            speed=speed or 0,
            etaSeconds=eta if eta else -1,
            message=f"下載中... {percent}%",
        )
        logger.debug(f"[{job_id}] Progress: {percent}% ({downloaded}/{total} bytes)")

    elif status == "finished":
        logger.info(f"[{job_id}] Download finished, processing...")
        _update_job(
            job_id,
            stage="processing",
            percent=95,
            message="處理中...",
        )


@downloads_bp.route("", methods=["POST"])
def submit_download() -> tuple:
    """
    提交新的下載任務
    ---
    tags:
      - downloads
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - url
            - format
          properties:
            url:
              type: string
              description: 媒體 URL（支援 YouTube、Instagram、Facebook、X）
            format:
              type: string
              enum: [mp4, mp3]
              description: 輸出格式
    responses:
      202:
        description: 任務已接受
      400:
        description: 請求參數錯誤
    """
    data = request.get_json() or {}
    logger.info(f"POST /api/downloads - Request data: {data}")

    # Validate required fields
    if "url" not in data:
        logger.warning("Missing required field: url")
        return jsonify({"error": "url is required"}), 400

    if "format" not in data:
        logger.warning("Missing required field: format")
        return jsonify({"error": "format is required"}), 400

    url = data["url"]
    fmt = data["format"]

    # Validate URL
    if not _is_valid_url(url):
        logger.warning(f"Invalid URL or unsupported platform: {url}")
        return jsonify({"error": "Invalid URL or unsupported platform"}), 400

    # Validate format
    if not _is_valid_format(fmt):
        logger.warning(f"Invalid format: {fmt}")
        return jsonify({"error": "Invalid format; must be one of: mp4, mp3"}), 400

    # Create job
    job_id = str(uuid.uuid4())
    platform = _get_platform(url)

    job = {
        "jobId": job_id,
        "status": "pending",
        "stage": "queued",
        "url": url,
        "format": fmt,
        "platform": platform,
        "percent": 0,
        "message": "任務已排隊",
    }

    with _jobs_lock:
        _jobs[job_id] = job

    logger.info(f"[{job_id}] Job created: platform={platform}, format={fmt}, url={url}")

    # Start download in background thread
    thread = threading.Thread(
        target=_run_download, args=(job_id, url, fmt), daemon=True
    )
    thread.start()
    logger.info(f"[{job_id}] Background download thread started")

    return jsonify(job), 202


@downloads_bp.route("/<job_id>", methods=["GET"])
def get_job_status(job_id: str) -> tuple:
    """
    取得任務狀態與結果
    ---
    tags:
      - downloads
    parameters:
      - name: job_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: 任務詳細資訊
      404:
        description: 任務不存在
    """
    logger.debug(f"GET /api/downloads/{job_id}")

    with _jobs_lock:
        if job_id not in _jobs:
            logger.warning(f"Job not found: {job_id}")
            return jsonify({"error": f"Job {job_id} not found"}), 404
        job = _jobs[job_id].copy()

    response = {
        "jobId": job_id,
        "status": job.get("status", "pending"),
        "stage": job.get("stage", "pending"),
        "url": job.get("url"),
        "format": job.get("format"),
        "platform": job.get("platform"),
        "title": job.get("title"),
        "downloadUrl": job.get("downloadUrl"),
        "fileSize": job.get("fileSize"),
        "error": job.get("error"),
    }

    return jsonify(response), 200


@downloads_bp.route("/<job_id>/progress", methods=["GET"])
def get_job_progress(job_id: str) -> tuple:
    """
    取得任務即時進度
    ---
    tags:
      - downloads
    parameters:
      - name: job_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: 任務進度資訊
      404:
        description: 任務不存在
    """
    with _jobs_lock:
        if job_id not in _jobs:
            logger.warning(f"Job not found for progress: {job_id}")
            return jsonify({"error": f"Job {job_id} not found"}), 404
        job = _jobs[job_id].copy()

    progress_response = {
        "jobId": job_id,
        "status": job.get("status", "pending"),
        "stage": job.get("stage", "pending"),
        "percent": job.get("percent", 0.0),
        "downloadedBytes": job.get("downloadedBytes", 0),
        "totalBytes": job.get("totalBytes", 0),
        "speed": job.get("speed", 0),
        "etaSeconds": job.get("etaSeconds", -1),
        "message": job.get("message", ""),
        "queueDepth": job.get("queueDepth", 0),
        "queuePosition": job.get("queuePosition", 0),
        "retryAfterSeconds": job.get("retryAfterSeconds"),
        "attemptsRemaining": job.get("attemptsRemaining"),
        "remediation": job.get("remediation"),
    }

    logger.debug(
        f"[{job_id}] Progress: status={progress_response['status']}, percent={progress_response['percent']}"
    )
    return jsonify(progress_response), 200


@downloads_bp.route("/<job_id>/file", methods=["GET"])
def download_file(job_id: str) -> tuple:
    """
    下載完成的檔案
    ---
    tags:
      - downloads
    parameters:
      - name: job_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: 檔案內容
      404:
        description: 任務或檔案不存在
    """
    logger.info(f"GET /api/downloads/{job_id}/file")

    with _jobs_lock:
        if job_id not in _jobs:
            logger.warning(f"Job not found for file download: {job_id}")
            return jsonify({"error": f"Job {job_id} not found"}), 404
        job = _jobs[job_id].copy()

    if job.get("status") != "completed":
        logger.warning(
            f"[{job_id}] File download attempted but job not completed: {job.get('status')}"
        )
        return jsonify({"error": "Download not completed yet"}), 400

    file_path = job.get("filePath")
    if not file_path or not Path(file_path).exists():
        logger.error(f"[{job_id}] File not found: {file_path}")
        return jsonify({"error": "File not found"}), 404

    logger.info(f"[{job_id}] Serving file: {file_path}")
    return send_file(
        file_path,
        as_attachment=True,
        download_name=Path(file_path).name,
    )
