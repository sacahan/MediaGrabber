#!/usr/bin/env python3
"""
Test for playlist video selection feature.

Tests that the selected_videos parameter works correctly.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from media_grabber_web import app


class TestPlaylistVideoSelection(unittest.TestCase):
    """Test playlist video selection functionality."""

    def setUp(self):
        """Set up test client."""
        self.client = app.test_client()
        self.client.testing = True

    def test_playlist_download_with_selected_videos(self):
        """Test starting a playlist download with selected videos."""
        # This test just verifies the API accepts the parameter
        response = self.client.post(
            "/playlist/download_start",
            json={
                "url": "https://www.youtube.com/watch?v=VeUiVCb7ZmQ&list=RDVeUiVCb7ZmQ",
                "format": "mp3",
                "delay": 1,
                "selected_videos": ["VeUiVCb7ZmQ", "fake_id_123"],  # Selected video IDs
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("job_id", data)

        print("\n✓ Playlist download started with selected videos")
        print(f"  Job ID: {data['job_id']}")

    def test_playlist_download_empty_selection(self):
        """Test that empty selection returns error."""
        response = self.client.post(
            "/playlist/download_start",
            json={
                "url": "https://www.youtube.com/playlist?list=PLtest",
                "format": "mp3",
                "selected_videos": [],  # Empty selection
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertIn("At least one video", data["error"])

        print("\n✓ Empty selection correctly rejected")
        print(f"  Error: {data['error']}")

    def test_playlist_download_invalid_selection_type(self):
        """Test that invalid selection type returns error."""
        response = self.client.post(
            "/playlist/download_start",
            json={
                "url": "https://www.youtube.com/playlist?list=PLtest",
                "format": "mp3",
                "selected_videos": "not_a_list",  # Invalid type
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertIn("must be a list", data["error"])

        print("\n✓ Invalid selection type correctly rejected")
        print(f"  Error: {data['error']}")

    def test_playlist_download_without_selection(self):
        """Test that playlist download works without selection (downloads all)."""
        response = self.client.post(
            "/playlist/download_start",
            json={
                "url": "https://www.youtube.com/watch?v=VeUiVCb7ZmQ&list=RDVeUiVCb7ZmQ",
                "format": "mp3",
                "delay": 1,
                # No selected_videos parameter - should download all
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("job_id", data)

        print("\n✓ Playlist download started without selection (all videos)")
        print(f"  Job ID: {data['job_id']}")


if __name__ == "__main__":
    print("=" * 70)
    print("Playlist Video Selection Feature Tests")
    print("=" * 70)
    print("\nTesting the new video selection functionality.\n")

    unittest.main(verbosity=2)
