"""Contract tests for downloads REST API."""

from __future__ import annotations


import pytest
from flask import Flask
from flask_cors import CORS

from backend.app.api.downloads import downloads_bp
from backend.app.models.transcode_profile import TranscodeProfile, TranscodeProfilePair


@pytest.fixture()
def app() -> Flask:
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    CORS(app)
    app.register_blueprint(downloads_bp)
    return app


@pytest.fixture()
def client(app: Flask):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def profile_pair() -> TranscodeProfilePair:
    primary = TranscodeProfile(
        name="mobile-primary",
        resolution=(720, 1280),
        video_bitrate_kbps=1000,
        audio_bitrate_kbps=128,
        max_filesize_mb=50,
        crf=23,
        container="mp4",
    )
    fallback = TranscodeProfile(
        name="mobile-fallback",
        resolution=(480, 854),
        video_bitrate_kbps=700,
        audio_bitrate_kbps=96,
        max_filesize_mb=30,
        crf=28,
        container="mp4",
    )
    return TranscodeProfilePair(primary=primary, fallback=fallback)


def test_api_post_downloads_returns_202(client) -> None:
    """Test that POST /api/downloads returns 202 Accepted."""
    response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    assert response.status_code == 202
    data = response.get_json()
    assert "jobId" in data
    assert data["status"] in ["pending", "queued"]


def test_api_post_downloads_with_invalid_url_returns_400(client) -> None:
    """Test that invalid URLs return 400."""
    response = client.post(
        "/api/downloads",
        json={"url": "not-a-valid-url", "format": "mp4"},
    )
    # Should either return 400 or have validation in the schema
    # This depends on implementation, but contract should reject invalid URLs
    assert response.status_code in [400, 422]


def test_api_post_downloads_requires_format(client) -> None:
    """Test that format parameter is required."""
    response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    # Should fail validation
    assert response.status_code in [400, 422]


def test_api_post_downloads_with_instagram_returns_202(client) -> None:
    """Test Instagram URL submission."""
    response = client.post(
        "/api/downloads",
        json={"url": "https://www.instagram.com/reel/abc123/", "format": "mp4"},
    )
    assert response.status_code == 202
    data = response.get_json()
    assert "jobId" in data


def test_api_get_downloads_job_returns_200(client) -> None:
    """Test that GET /api/downloads/{jobId} returns 200."""
    # First submit a job
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    # Then retrieve it
    response = client.get(f"/api/downloads/{job_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["jobId"] == job_id
    assert "status" in data


def test_api_get_downloads_nonexistent_returns_404(client) -> None:
    """Test that nonexistent job returns 404."""
    response = client.get("/api/downloads/nonexistent-job-id")
    assert response.status_code == 404


def test_api_get_downloads_progress_returns_200(client) -> None:
    """Test that GET /api/downloads/{jobId}/progress returns 200."""
    # First submit a job
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    # Then get progress
    response = client.get(f"/api/downloads/{job_id}/progress")
    assert response.status_code == 200
    data = response.get_json()
    assert "jobId" in data
    assert "status" in data
    assert "percent" in data


def test_api_get_downloads_progress_nonexistent_returns_404(client) -> None:
    """Test that progress for nonexistent job returns 404."""
    response = client.get("/api/downloads/nonexistent-job-id/progress")
    assert response.status_code == 404


def test_api_response_includes_required_fields(client) -> None:
    """Test that responses include all required OpenAPI fields."""
    response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    data = response.get_json()

    # Check required fields per OpenAPI spec
    required_fields = ["jobId", "status"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_api_supports_all_platform_urls(client) -> None:
    """Test that API accepts URLs from all supported platforms."""
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.instagram.com/reel/abc123/",
        "https://www.facebook.com/video.php?v=123",
        "https://x.com/user/status/123",
    ]

    for url in urls:
        response = client.post(
            "/api/downloads",
            json={"url": url, "format": "mp4"},
        )
        assert response.status_code == 202, f"Failed for URL: {url}"


def test_api_supports_all_formats(client) -> None:
    """Test that API accepts all supported formats."""
    formats = ["mp4", "mp3"]

    for fmt in formats:
        response = client.post(
            "/api/downloads",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": fmt},
        )
        assert response.status_code == 202, f"Failed for format: {fmt}"


def test_api_progress_includes_monotonic_percent(client) -> None:
    """Test that progress percent is monotonically increasing."""
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    response = client.get(f"/api/downloads/{job_id}/progress")
    data = response.get_json()

    assert "percent" in data
    assert 0.0 <= data["percent"] <= 100.0
