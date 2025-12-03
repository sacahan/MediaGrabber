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
    """Submit a new download job."""
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
    """Get job status and artifacts."""
    if job_id not in _jobs:
        return jsonify({"error": f"Job {job_id} not found"}), 404

    return jsonify(_jobs[job_id]), 200


@downloads_bp.route("/<job_id>/progress", methods=["GET"])
def get_job_progress(job_id: str) -> tuple:
    """Get real-time progress for a job."""
    if job_id not in _jobs:
        return jsonify({"error": f"Job {job_id} not found"}), 404

    job = _jobs[job_id]
    return jsonify(
        {
            "jobId": job_id,
            "status": job.get("status", "downloading"),
            "percent": 0.0,
            "message": "",
        }
    ), 200
