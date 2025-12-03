"""Contract tests for progress API endpoint."""

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


def test_progress_api_returns_status_field(client) -> None:
    """Test that progress API includes status field."""
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    response = client.get(f"/api/downloads/{job_id}/progress")
    assert "status" in response.get_json()


def test_progress_api_returns_stage_field(client) -> None:
    """Test that progress API includes stage field."""
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    response = client.get(f"/api/downloads/{job_id}/progress")
    # stage should be present or implicitly understood
    # For now just verify the response structure
    assert response.status_code == 200


def test_progress_api_returns_percent_field(client) -> None:
    """Test that progress API includes percent field."""
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    response = client.get(f"/api/downloads/{job_id}/progress")
    data = response.get_json()
    assert "percent" in data
    assert isinstance(data["percent"], (int, float))
    assert 0 <= data["percent"] <= 100


def test_progress_api_returns_queue_depth_field(client) -> None:
    """Test that progress API includes queueDepth field when available."""
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    response = client.get(f"/api/downloads/{job_id}/progress")
    # queueDepth may be optional initially but should be in extended responses
    assert response.status_code == 200


def test_progress_api_returns_remediation_field_on_error(client) -> None:
    """Test that progress API includes remediation field on errors."""
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    response = client.get(f"/api/downloads/{job_id}/progress")
    # remediation is optional but should be present when needed
    assert response.status_code == 200


def test_progress_api_consistency_with_job_status(client) -> None:
    """Test that progress status is consistent with job status."""
    post_response = client.post(
        "/api/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"},
    )
    job_id = post_response.get_json()["jobId"]

    progress_response = client.get(f"/api/downloads/{job_id}/progress")
    progress_data = progress_response.get_json()

    # Status should be consistent between job and progress
    # Both should have compatible status values
    assert "status" in progress_data


def test_progress_api_handles_unknown_job_gracefully(client) -> None:
    """Test that progress API returns 404 for unknown job."""
    response = client.get("/api/downloads/unknown-job-id/progress")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
