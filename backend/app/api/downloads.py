"""Flask blueprint for downloads API with actual yt-dlp integration."""

from __future__ import annotations

import atexit
import asyncio
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

# 導入轉碼相關服務
from ..services.transcode_service import TranscodeService
from ..services.transcode_queue import TranscodeQueue
from ..services.progress_bus import ProgressBus
from ..models.transcode_profile import (
    PROFILE_FAST_1080P30_PRIMARY,
    PROFILE_FAST_1080P30_FALLBACK,
    TranscodeProfilePair,
)
from ..models.download_job import DownloadJob

# Configure module logger
logger = logging.getLogger(__name__)

downloads_bp = Blueprint("downloads", __name__)

# In-memory job store (production would use DB)
_jobs: dict = {}
_jobs_lock = threading.Lock()

# 初始化轉碼服務
_progress_bus = ProgressBus(ttl_seconds=3600)
_transcode_queue = TranscodeQueue(max_workers=2)  # 最多同時轉碼 2 個檔案
_transcode_service = TranscodeService(_transcode_queue, _progress_bus)

# 轉碼設定檔配對（主要 + 備用）
_transcode_profile_pair = TranscodeProfilePair(
    primary=PROFILE_FAST_1080P30_PRIMARY,
    fallback=PROFILE_FAST_1080P30_FALLBACK,
)

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
        elif "threads.net" in netloc or "threads.com" in netloc:
            return "threads"
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


def _download_threads_manual(
    job_id: str, url: str, cookies_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Download Threads video by manually parsing the page.

    yt-dlp doesn't officially support Threads yet, so we need to:
    1. Fetch the page HTML with cookies
    2. Extract video URL from embedded JSON data
    3. Download the video directly

    Returns the downloaded file path, or None if failed.
    """
    import json
    import re

    import requests
    from http.cookiejar import MozillaCookieJar

    logger.info(f"[{job_id}] Using manual Threads parser...")
    _update_job(
        job_id,
        status="downloading",
        stage="parsing",
        percent=10,
        message="解析 Threads 頁面...",
    )

    # Extract post ID from URL
    match = re.search(r"/(?:post|t)/([^/?#&]+)", url)
    if not match:
        raise Exception("無法從 URL 提取貼文 ID")

    post_id = match.group(1)
    logger.info(f"[{job_id}] Threads post ID: {post_id}")

    # Set up session with cookies
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    # Load cookies if provided
    if cookies_path and cookies_path.exists():
        try:
            cookie_jar = MozillaCookieJar(str(cookies_path))
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cookie_jar
            logger.info(f"[{job_id}] Loaded {len(cookie_jar)} cookies")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to load cookies: {e}")

    # Fetch the page
    _update_job(job_id, percent=20, message="下載頁面內容...")
    response = session.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    webpage = response.text
    logger.info(f"[{job_id}] Page size: {len(webpage)} bytes")

    # Search for JSON data containing post info
    _update_job(job_id, percent=30, message="提取影片資訊...")

    video_url = None

    # Strategy 1: Find video_url directly in HTML
    video_url_match = re.search(r'"video_url"\s*:\s*"([^"]+)"', webpage)
    if video_url_match:
        video_url = video_url_match.group(1).replace("\\u0026", "&").replace("\\/", "/")
        logger.info(f"[{job_id}] Found video_url in HTML")

    # Strategy 2: Look for CDN video links
    if not video_url:
        cdn_match = re.search(
            r'(https?://[^"\']*?scontent[^"\']*?\.mp4[^"\']*)', webpage
        )
        if cdn_match:
            video_url = cdn_match.group(1).replace("\\u0026", "&").replace("\\/", "/")
            logger.info(f"[{job_id}] Found CDN video URL")

    # Strategy 3: Parse JSON script tags
    if not video_url:
        json_scripts = re.findall(
            r'<script type="application/json"[^>]*?\sdata-sjs[^>]*?>(.*?)</script>',
            webpage,
            re.DOTALL | re.IGNORECASE,
        )
        logger.info(f"[{job_id}] Found {len(json_scripts)} JSON script tags")

        for script in json_scripts:
            if post_id not in script:
                continue

            try:
                parsed = json.loads(script)

                # Recursive search for video_versions
                def find_video_url(data, depth=0):
                    if depth > 30:
                        return None
                    if isinstance(data, dict):
                        if "video_versions" in data and data.get("video_versions"):
                            versions = data["video_versions"]
                            if versions:
                                # Get highest quality (first one is usually best)
                                return versions[0].get("url")
                        for value in data.values():
                            result = find_video_url(value, depth + 1)
                            if result:
                                return result
                    elif isinstance(data, list):
                        for item in data:
                            result = find_video_url(item, depth + 1)
                            if result:
                                return result
                    return None

                found_url = find_video_url(parsed)
                if found_url:
                    video_url = found_url.replace("\\u0026", "&").replace("\\/", "/")
                    logger.info(f"[{job_id}] Found video URL in JSON data")
                    break
            except json.JSONDecodeError:
                continue

    if not video_url:
        raise Exception("無法從頁面提取影片 URL，可能需要登入或此貼文不包含影片")

    # Download the video
    _update_job(job_id, percent=50, message="下載影片中...")
    logger.info(f"[{job_id}] Downloading video from: {video_url[:80]}...")

    video_response = session.get(video_url, headers=headers, stream=True, timeout=60)
    video_response.raise_for_status()

    # Get total size for progress
    total_size = int(video_response.headers.get("content-length", 0))

    # Create output directory and file
    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r'[<>:"/\\|?*]', "_", f"threads_{post_id}")
    output_file = job_output_dir / f"{safe_title}.mp4"

    downloaded = 0
    with open(output_file, "wb") as f:
        for chunk in video_response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = min(95, 50 + int((downloaded / total_size) * 45))
                _update_job(
                    job_id,
                    percent=percent,
                    downloadedBytes=downloaded,
                    totalBytes=total_size,
                    message=f"下載中... {percent}%",
                )

    file_size = output_file.stat().st_size
    logger.info(f"[{job_id}] Downloaded: {output_file} ({file_size} bytes)")

    return output_file


def _run_download(
    job_id: str, url: str, fmt: str, cookies_path: Optional[Path] = None
) -> None:
    """Execute download in background thread using yt-dlp or manual parser."""
    logger.info(f"[{job_id}] Starting download: url={url}, format={fmt}")

    platform = _get_platform(url)

    # Create output directory for the job
    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)

    # Use manual parser for Threads (yt-dlp doesn't support it yet)
    if platform == "threads":
        try:
            _update_job(
                job_id,
                status="downloading",
                stage="initializing",
                percent=5,
                message="初始化 Threads 下載...",
            )

            downloaded_file = _download_threads_manual(job_id, url, cookies_path)

            if downloaded_file and downloaded_file.exists():
                file_size = downloaded_file.stat().st_size
                logger.info(
                    f"[{job_id}] File saved: {downloaded_file} ({file_size} bytes)"
                )

                # 應用轉碼（如果需要）
                final_file = _apply_transcode(
                    job_id, downloaded_file, fmt, downloaded_file.stem, job_output_dir
                )

                final_file_size = final_file.stat().st_size
                logger.info(
                    f"[{job_id}] Final file: {final_file} ({final_file_size} bytes)"
                )

                _update_job(
                    job_id,
                    status="completed",
                    stage="completed",
                    percent=100,
                    message="下載完成！",
                    title=final_file.stem,
                    filePath=str(final_file),
                    fileSize=final_file_size,
                    downloadUrl=f"/api/downloads/{job_id}/file",
                )
            else:
                raise Exception("下載的檔案不存在")

        except Exception as e:
            logger.error(f"[{job_id}] Threads download failed: {e}", exc_info=True)
            _update_job(
                job_id,
                status="failed",
                stage="error",
                percent=0,
                message=f"下載失敗: {str(e)}",
                error=str(e),
            )
        return

    # Use yt-dlp for other platforms
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

        # Add cookies if provided (takes priority over platform-specific defaults)
        if cookies_path and cookies_path.exists():
            ydl_opts["cookiefile"] = str(cookies_path)
            logger.info(f"[{job_id}] Using cookies from: {cookies_path}")
        else:
            # Platform-specific default cookies (Threads is handled separately above)
            if platform == "instagram":
                # Instagram often needs cookies for best results
                instagram_cookies = (
                    Path(__file__).parent.parent.parent / "cookies" / "instagram.txt"
                )
                if instagram_cookies.exists():
                    ydl_opts["cookiefile"] = str(instagram_cookies)
                    logger.info(
                        f"[{job_id}] Using Instagram cookies: {instagram_cookies}"
                    )

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

                # 應用轉碼（如果需要）
                final_file = _apply_transcode(
                    job_id, downloaded_file, fmt, title, job_output_dir
                )

                final_file_size = final_file.stat().st_size
                logger.info(
                    f"[{job_id}] Final file: {final_file} ({final_file_size} bytes)"
                )

                _update_job(
                    job_id,
                    status="completed",
                    stage="completed",
                    percent=100,
                    message="下載完成！",
                    title=title,
                    filePath=str(final_file),
                    fileSize=final_file_size,
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


def _apply_transcode(
    job_id: str, downloaded_file: Path, fmt: str, title: str, output_dir: Path
) -> Path:
    """應用轉碼（強制對所有 MP4 檔案進行轉碼）。

    對於所有 MP4 檔案，強制執行轉碼以確保相容性和一致性。
    對於 MP3 檔案，返回原檔案（已由 yt-dlp 提取）。

    Args:
        job_id: 任務 ID
        downloaded_file: 下載的檔案路徑
        fmt: 要求的格式（mp4 或 mp3）
        title: 影片標題
        output_dir: 輸出目錄

    Returns:
        最終檔案的路徑
    """
    # 只對 MP4 檔案進行轉碼
    if fmt != "mp4":
        logger.debug(f"[{job_id}] Skipping transcode for {fmt} format")
        return downloaded_file

    # 檢查檔案是否是 MP4
    if not downloaded_file.suffix.lower() == ".mp4":
        logger.debug(f"[{job_id}] Downloaded file is {downloaded_file.suffix}, not MP4")
        return downloaded_file

    # 強制轉碼所有 MP4 檔案
    file_size_mb = downloaded_file.stat().st_size / (1024 * 1024)
    logger.info(
        f"[{job_id}] Starting mandatory transcode for: {downloaded_file.name} ({file_size_mb:.2f} MB)"
    )

    _update_job(
        job_id,
        status="transcoding",
        stage="transcoding",
        percent=96,
        message="轉碼中...",
    )

    try:
        # 訂閱進度匯流排以更新任務進度
        def on_progress(state):
            if state.job_id == job_id:
                _update_job(
                    job_id,
                    percent=state.percent,
                    message=state.message,
                )

        _progress_bus.subscribe(on_progress)

        try:
            # 建立 DownloadJob 物件用於轉碼服務
            job = DownloadJob(
                job_id=job_id,
                source_url="",  # 轉碼時不需要來源 URL
                platform="youtube",  # 此值在轉碼時不重要
                requested_format=fmt,
                download_backend="yt-dlp",
                profile=_transcode_profile_pair,
                output_dir=output_dir,
            )

            # 準備輸出檔案路徑
            output_file = output_dir / f"{title}_transcoded.mp4"

            # 使用事件迴圈執行轉碼
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    _transcode_service.transcode_primary(
                        job, downloaded_file, output_file, _transcode_profile_pair
                    )
                )
            finally:
                loop.close()

            if result.error:
                logger.error(f"[{job_id}] Transcode error: {result.error.message}")
                _update_job(
                    job_id,
                    message=f"轉碼失敗: {result.error.message}",
                )
                # 返回原始檔案作為備選
                return downloaded_file

            if output_file.exists():
                output_size_mb = output_file.stat().st_size / (1024 * 1024)
                compression_ratio = result.compression_ratio
                logger.info(
                    f"[{job_id}] Transcode completed: {output_file.name} "
                    f"({output_size_mb:.2f} MB, compression ratio: {compression_ratio:.2%})"
                )

                # 刪除原始下載檔案
                try:
                    downloaded_file.unlink()
                    logger.debug(f"[{job_id}] Removed original file: {downloaded_file}")
                except Exception as e:
                    logger.warning(f"[{job_id}] Failed to remove original file: {e}")

                return output_file
            else:
                logger.warning(f"[{job_id}] Transcode output file not created")
                return downloaded_file

        finally:
            _progress_bus.unsubscribe(on_progress)

    except Exception as e:
        logger.error(f"[{job_id}] Transcode failed: {e}", exc_info=True)
        _update_job(
            job_id,
            message=f"轉碼失敗: {str(e)}",
        )
        # 返回原始檔案作為備選
        return downloaded_file


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
              description: 媒體 URL（支援 YouTube、Instagram、Facebook、X、Threads）
            format:
              type: string
              enum: [mp4, mp3]
              description: 輸出格式
            cookiesBase64:
              type: string
              description: Base64 編碼的 Netscape cookies.txt 內容（用於需要認證的平台如 Threads）
    responses:
      202:
        description: 任務已接受
      400:
        description: 請求參數錯誤
    """
    import base64

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
    cookies_base64 = data.get("cookiesBase64")

    # Validate URL
    if not _is_valid_url(url):
        logger.warning(f"Invalid URL or unsupported platform: {url}")
        return jsonify({"error": "Invalid URL or unsupported platform"}), 400

    # Validate format
    if not _is_valid_format(fmt):
        logger.warning(f"Invalid format: {fmt}")
        return jsonify({"error": "Invalid format; must be one of: mp4, mp3"}), 400

    # Process cookies if provided
    cookies_path = None
    platform = _get_platform(url)

    if cookies_base64:
        try:
            # Decode base64 cookies
            cookies_content = base64.b64decode(cookies_base64).decode("utf-8")
            logger.debug(
                f"Decoded cookies content length: {len(cookies_content)} chars"
            )

            # Create job-specific cookies file
            job_id = str(uuid.uuid4())
            job_cookies_dir = OUTPUT_DIR / job_id
            job_cookies_dir.mkdir(parents=True, exist_ok=True)
            cookies_path = job_cookies_dir / "cookies.txt"
            cookies_path.write_text(cookies_content, encoding="utf-8")
            logger.info(f"[{job_id}] Cookies saved to: {cookies_path}")
        except Exception as e:
            logger.warning(f"Failed to decode cookies: {e}")
            return jsonify({"error": f"Invalid cookies format: {str(e)}"}), 400
    else:
        job_id = str(uuid.uuid4())

    # Validate Threads requires cookies
    if platform == "threads" and not cookies_path:
        # Check for default cookies files
        threads_cookies = (
            Path(__file__).parent.parent.parent / "cookies" / "threads.txt"
        )
        instagram_cookies = (
            Path(__file__).parent.parent.parent / "cookies" / "instagram.txt"
        )
        if not threads_cookies.exists() and not instagram_cookies.exists():
            logger.warning(
                f"[{job_id}] Threads download requires cookies but none provided"
            )
            # Allow the download to proceed - yt-dlp will handle the error

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
        target=_run_download, args=(job_id, url, fmt, cookies_path), daemon=True
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
