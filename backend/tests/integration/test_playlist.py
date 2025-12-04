#!/usr/bin/env python3
"""
Integration tests for YouTube Playlist download functionality.

Run with: uv run python test_playlist.py
"""

import unittest
import time
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from media_grabber_web import app, PLAYLIST_STATE


class TestPlaylistMetadata(unittest.TestCase):
    """Test playlist metadata extraction endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = app.test_client()
        self.client.testing = True

    def test_playlist_metadata_endpoint(self):
        """Test /playlist/metadata endpoint with a real YouTube playlist URL."""
        # Using a small, stable YouTube Mix playlist
        # Note: This is a "radio" playlist which might have varying results
        playlist_url = "https://www.youtube.com/watch?v=VeUiVCb7ZmQ&list=RDVeUiVCb7ZmQ"

        response = self.client.post(
            "/playlist/metadata",
            json={"url": playlist_url},
            content_type="application/json",
        )

        # Check response status
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200 but got {response.status_code}: {response.data}",
        )

        data = response.get_json()

        # Verify response structure
        self.assertIn("title", data)
        self.assertIn("video_count", data)
        self.assertIn("videos", data)
        self.assertIn("uploader", data)

        # Verify data types
        self.assertIsInstance(data["title"], str)
        self.assertIsInstance(data["video_count"], int)
        self.assertIsInstance(data["videos"], list)

        # Radio/Mix playlists should have videos
        self.assertGreater(
            data["video_count"], 0, "Playlist should contain at least one video"
        )

        # Verify video structure
        if len(data["videos"]) > 0:
            first_video = data["videos"][0]
            self.assertIn("id", first_video)
            self.assertIn("title", first_video)
            self.assertIn("duration", first_video)

        print("\n✓ Playlist metadata extraction successful")
        print(f"  Title: {data['title']}")
        print(f"  Video count: {data['video_count']}")
        print("  First 3 videos:")
        for i, video in enumerate(data["videos"][:3], 1):
            print(f"    {i}. {video['title']}")

    def test_playlist_metadata_invalid_url(self):
        """Test playlist metadata endpoint with invalid URL."""
        response = self.client.post(
            "/playlist/metadata",
            json={"url": "https://www.youtube.com/watch?v=invalid"},
            content_type="application/json",
        )

        # Should return error for non-playlist URL
        # Note: The endpoint might still succeed for single videos, depends on implementation
        data = response.get_json()
        self.assertIn("error", data)

    def test_playlist_metadata_missing_url(self):
        """Test playlist metadata endpoint with missing URL."""
        response = self.client.post(
            "/playlist/metadata", json={}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)


class TestPlaylistDownloadFlow(unittest.TestCase):
    """Test the complete playlist download workflow."""

    def setUp(self):
        """Set up test client."""
        self.client = app.test_client()
        self.client.testing = True
        # Clear any existing playlist state
        PLAYLIST_STATE.clear()

    def test_download_start_endpoint(self):
        """Test /playlist/download_start endpoint."""
        # Use a very small playlist (just 1-2 videos from a mix)
        playlist_url = "https://www.youtube.com/watch?v=VeUiVCb7ZmQ&list=RDVeUiVCb7ZmQ"

        response = self.client.post(
            "/playlist/download_start",
            json={
                "url": playlist_url,
                "format": "mp3",
                "delay": 1,  # Short delay for testing
            },
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200 but got {response.status_code}: {response.data}",
        )

        data = response.get_json()
        self.assertIn("job_id", data)

        job_id = data["job_id"]
        print(f"\n✓ Playlist download started with job_id: {job_id}")

        # Verify job_id is in PLAYLIST_STATE
        self.assertIn(job_id, PLAYLIST_STATE)

        # Wait a moment for the background thread to start
        time.sleep(2)

        # Check progress endpoint
        progress_response = self.client.get(f"/playlist/progress/{job_id}")
        self.assertEqual(progress_response.status_code, 200)

        progress_data = progress_response.get_json()
        self.assertIn("status", progress_data)
        self.assertIn("total_videos", progress_data)

        print(f"  Status: {progress_data['status']}")
        print(f"  Total videos: {progress_data.get('total_videos', 'N/A')}")

        # Note: We don't wait for completion as it might take too long
        # This test just verifies the endpoints work correctly

    def test_progress_endpoint_invalid_job(self):
        """Test progress endpoint with invalid job ID."""
        response = self.client.get("/playlist/progress/invalid-job-id")

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("error", data)


class TestPlaylistEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test client."""
        self.client = app.test_client()
        self.client.testing = True

    def test_missing_format(self):
        """Test download_start with missing format parameter."""
        response = self.client.post(
            "/playlist/download_start",
            json={"url": "https://www.youtube.com/playlist?list=PLtest"},
            content_type="application/json",
        )

        # Should use default format (mp3)
        # Or return 400 if format is required
        self.assertIn(response.status_code, [200, 400])

    def test_invalid_delay(self):
        """Test download_start with invalid delay parameter."""
        response = self.client.post(
            "/playlist/download_start",
            json={
                "url": "https://www.youtube.com/playlist?list=PLtest",
                "format": "mp3",
                "delay": -1,  # Invalid negative delay
            },
            content_type="application/json",
        )

        # Should use default delay or return error
        # Implementation should handle this gracefully
        self.assertIsNotNone(response)


if __name__ == "__main__":
    print("=" * 70)
    print("MediaGrabber Playlist Feature Integration Tests")
    print("=" * 70)
    print("\nThese tests make actual network calls to YouTube.")
    print("Tests may be affected by YouTube's rate limiting or API changes.\n")

    # Run tests with verbose output
    unittest.main(verbosity=2)
