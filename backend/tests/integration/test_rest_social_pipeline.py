"""Integration tests for REST API with social media downloads."""

from __future__ import annotations


import pytest
from flask import Flask
from flask_cors import CORS

from backend.app.api.downloads import downloads_bp


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


def test_rest_instagram_workflow(client) -> None:
    """Test complete Instagram download workflow."""
    # Submit job
    response = client.post(
        "/api/downloads",
        json={
            "url": "https://www.instagram.com/reel/abc123/",
            "format": "mp4",
        },
    )
    assert response.status_code == 202
    job_id = response.get_json()["jobId"]

    # Retrieve job
    response = client.get(f"/api/downloads/{job_id}")
    assert response.status_code == 200
    job_data = response.get_json()
    assert job_data["jobId"] == job_id

    # Get progress
    response = client.get(f"/api/downloads/{job_id}/progress")
    assert response.status_code == 200
    progress = response.get_json()
    assert "percent" in progress
    assert 0.0 <= progress["percent"] <= 100.0


def test_rest_facebook_workflow(client) -> None:
    """Test Facebook video download workflow."""
    response = client.post(
        "/api/downloads",
        json={
            "url": "https://www.facebook.com/video.php?v=123",
            "format": "mp4",
        },
    )
    assert response.status_code == 202
    job_id = response.get_json()["jobId"]

    # Verify job exists
    response = client.get(f"/api/downloads/{job_id}")
    assert response.status_code == 200


def test_rest_x_workflow(client) -> None:
    """Test X/Twitter video download workflow."""
    response = client.post(
        "/api/downloads",
        json={
            "url": "https://x.com/user/status/123456789",
            "format": "mp4",
        },
    )
    assert response.status_code == 202


def test_rest_youtube_as_social(client) -> None:
    """Test that YouTube URLs are also accepted via REST."""
    response = client.post(
        "/api/downloads",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format": "mp4",
        },
    )
    assert response.status_code == 202


def test_rest_concurrent_jobs(client) -> None:
    """Test that API can handle multiple concurrent job submissions."""
    job_ids = []
    urls = [
        "https://www.instagram.com/reel/abc123/",
        "https://www.facebook.com/video.php?v=123",
        "https://x.com/user/status/123",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ]

    # Submit multiple jobs
    for url in urls:
        response = client.post(
            "/api/downloads",
            json={"url": url, "format": "mp4"},
        )
        assert response.status_code == 202
        job_ids.append(response.get_json()["jobId"])

    # Verify all jobs exist
    for job_id in job_ids:
        response = client.get(f"/api/downloads/{job_id}")
        assert response.status_code == 200


def test_rest_formats_per_platform(client) -> None:
    """Test format support varies by platform."""
    # YouTube supports both mp4 and mp3
    for fmt in ["mp4", "mp3"]:
        response = client.post(
            "/api/downloads",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format": fmt,
            },
        )
        assert response.status_code == 202, f"YouTube format {fmt} failed"

    # Social platforms support mp4
    response = client.post(
        "/api/downloads",
        json={
            "url": "https://www.instagram.com/reel/abc123/",
            "format": "mp4",
        },
    )
    assert response.status_code == 202


def test_rest_progress_payload_structure(client) -> None:
    """Test that progress payload has expected structure."""
    # Submit job
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.instagram.com/reel/abc123/", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    # Get progress
    response = client.get(f"/api/downloads/{job_id}/progress")
    assert response.status_code == 200

    progress = response.get_json()
    # Verify expected fields
    expected_fields = ["jobId", "status", "percent", "message"]
    for field in expected_fields:
        assert field in progress, f"Missing field: {field}"
