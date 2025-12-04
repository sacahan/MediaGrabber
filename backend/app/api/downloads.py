"""Flask blueprint for downloads API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from urllib.parse import urlparse

downloads_bp = Blueprint("downloads", __name__, url_prefix="/api/downloads")

# Simple in-memory job store (placeholder; production would use DB)
_jobs = {}


def _is_valid_url(url: str) -> bool:
    """Validate URL format and supported platforms."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        # Check for supported platforms
        netloc_lower = parsed.netloc.lower()
        supported = [
            "youtube.com",
            "youtu.be",
            "instagram.com",
            "facebook.com",
            "x.com",
            "twitter.com",
        ]
        return any(domain in netloc_lower for domain in supported)
    except Exception:
        return False


def _is_valid_format(fmt: str) -> bool:
    """Validate format parameter."""
    return fmt in ["mp4", "mp3"]


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
              example: https://youtu.be/dQw4w9WgXcQ
            format:
              type: string
              enum: [mp4, mp3]
              description: 輸出格式
              example: mp4
    responses:
      202:
        description: 任務已接受
      400:
        description: 請求參數錯誤
    """
    data = request.get_json() or {}

    # Validate required fields
    if "url" not in data:
        return jsonify({"error": "url is required"}), 400

    if "format" not in data:
        return jsonify({"error": "format is required"}), 400

    url = data["url"]
    fmt = data["format"]

    # Validate URL
    if not _is_valid_url(url):
        return jsonify({"error": "Invalid URL or unsupported platform"}), 400

    # Validate format
    if not _is_valid_format(fmt):
        return jsonify({"error": "Invalid format; must be one of: mp4, mp3"}), 400

    # Create job
    import uuid

    job_id = str(uuid.uuid4())
    job = {
        "jobId": job_id,
        "status": "pending",
        "url": url,
        "format": fmt,
    }
    _jobs[job_id] = job

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
        description: 任務 ID
    responses:
      200:
        description: 任務詳細資訊
      404:
        description: 任務不存在
    """
    if job_id not in _jobs:
        return jsonify({"error": f"Job {job_id} not found"}), 404

    job = _jobs[job_id]

    # Build response with compression metrics (T033: US3)
    response = {
        "jobId": job_id,
        "status": job.get("status", "pending"),
        "url": job.get("url"),
        "format": job.get("format"),
        "downloadUrl": job.get("downloadUrl"),
        "isPlaylist": job.get("isPlaylist", False),
        # Compression & artifacts (T033)
        "compressionRatio": job.get("compressionRatio", None),
        "originalSize": job.get("originalSize", None),
        "compressedSize": job.get("compressedSize", None),
        "artifactPaths": job.get("artifactPaths", []),
        "summaryJson": job.get("summaryJson", None),  # Playlist summary path
        "compressionReport": job.get("compressionReport", None),  # Compression stats
        # Remediation (T033)
        "remediation": job.get("remediation", None),
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
        description: 任務 ID
    responses:
      200:
        description: 任務進度資訊
      404:
        description: 任務不存在
    """
    if job_id not in _jobs:
        return jsonify({"error": f"Job {job_id} not found"}), 404

    job = _jobs[job_id]

    # Build progress response with retry & remediation fields (T045)
    progress_response = {
        "jobId": job_id,
        "status": job.get("status", "downloading"),
        "stage": job.get("stage", "pending"),
        "percent": job.get("percent", 0.0),
        "downloadedBytes": job.get("downloadedBytes", 0),
        "totalBytes": job.get("totalBytes", 0),
        "speed": job.get("speed", 0),
        "etaSeconds": job.get("etaSeconds", -1),
        "message": job.get("message", ""),
        # Queue metrics (US2/US3)
        "queueDepth": job.get("queueDepth", 0),
        "queuePosition": job.get("queuePosition", 0),
        # Retry policy fields (T045: FR-007)
        "retryAfterSeconds": job.get("retryAfterSeconds", None),
        "attemptsRemaining": job.get("attemptsRemaining", None),
        # Remediation suggestion (US3)
        "remediation": job.get("remediation", None),
    }

    return jsonify(progress_response), 200
