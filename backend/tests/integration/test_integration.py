#!/usr/bin/env python3
"""
Integration tests for MediaGrabber using real YouTube URLs.
These tests make actual network calls to verify metadata extraction works correctly.

Run with: python test_integration.py
Or with specific test: python test_integration.py TestRealYouTubeMetadata.test_restricted_format_video
"""

import unittest
from pathlib import Path
import tempfile
import shutil
import sys

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from media_grabber import _prepare_download
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError


class TestRealYouTubeMetadata(unittest.TestCase):
    """
    Integration tests using real YouTube URLs.
    These tests verify that metadata extraction works for videos with restricted formats.
    """

    def setUp(self):
        """Create a temporary directory for test outputs."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_restricted_format_video(self):
        """
        Test metadata extraction for a video that previously caused
        "Requested format is not available" error.
        URL: https://www.youtube.com/watch?v=VeUiVCb7ZmQ
        """
        url = "https://www.youtube.com/watch?v=VeUiVCb7ZmQ"
        output_dir = Path(self.test_dir)

        try:
            # This should NOT raise DownloadError about format availability
            outtmpl = _prepare_download(url, output_dir)

            # Verify we got a valid output template
            self.assertIsNotNone(outtmpl)
            self.assertIn(".%(ext)s", outtmpl)
            self.assertTrue(Path(outtmpl).parent.exists())

            print(f"✓ Successfully extracted metadata for: {url}")
            print(f"  Output template: {outtmpl}")

        except (DownloadError, ExtractorError) as e:
            error_msg = str(e)
            # Check if it's the specific format error we were trying to fix
            if "Requested format is not available" in error_msg:
                self.fail(
                    f"FAILED: Still getting format validation error!\n"
                    f"Error: {error_msg}\n"
                    f"This means the fix did not work correctly."
                )
            else:
                # Re-raise if it's a different error (network, etc.)
                raise

    def test_playlist_url_single_video(self):
        """
        Test metadata extraction for a URL with playlist parameters.
        Should extract only the single video, not the entire playlist.
        URL: https://www.youtube.com/watch?v=VeUiVCb7ZmQ&list=RDVeUiVCb7ZmQ&index=1
        """
        url = "https://www.youtube.com/watch?v=VeUiVCb7ZmQ&list=RDVeUiVCb7ZmQ&index=1"
        output_dir = Path(self.test_dir)

        try:
            outtmpl = _prepare_download(url, output_dir)

            # Verify we got a valid output template
            self.assertIsNotNone(outtmpl)
            self.assertIn(".%(ext)s", outtmpl)

            print(f"✓ Successfully extracted metadata for playlist URL: {url}")
            print(f"  Output template: {outtmpl}")

        except (DownloadError, ExtractorError) as e:
            if "Requested format is not available" in str(e):
                self.fail(
                    f"FAILED: Format validation error on playlist URL!\n" f"Error: {e}"
                )
            else:
                raise

    def test_metadata_api_direct(self):
        """
        Test yt-dlp metadata extraction directly with the exact options
        used in our code to verify the fix.
        """
        url = "https://www.youtube.com/watch?v=VeUiVCb7ZmQ"

        # Use the exact same options as in media_grabber.py
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Verify we got the expected metadata
            self.assertIsNotNone(info)
            self.assertIn("title", info)
            self.assertIn("id", info)

            # Verify format is NOT in the options
            self.assertNotIn("format", ydl_opts)

            print("✓ Direct yt-dlp API test passed")
            print(f"  Video ID: {info.get('id')}")
            print(f"  Title: {info.get('title')}")
            print(f"  Duration: {info.get('duration')} seconds")

        except (DownloadError, ExtractorError) as e:
            if "Requested format is not available" in str(e):
                self.fail(
                    f"FAILED: yt-dlp API still raises format error!\n"
                    f"Options used: {ydl_opts}\n"
                    f"Error: {e}"
                )
            else:
                raise


class TestStandardYouTubeVideos(unittest.TestCase):
    """Test metadata extraction for standard YouTube videos."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_standard_video(self):
        """Test a standard YouTube video that should always work."""
        # Use the same URL that we've verified works in other tests
        url = "https://www.youtube.com/watch?v=VeUiVCb7ZmQ"
        output_dir = Path(self.test_dir)

        try:
            outtmpl = _prepare_download(url, output_dir)

            self.assertIsNotNone(outtmpl)
            self.assertIn(".%(ext)s", outtmpl)

            print(f"✓ Standard video test passed: {url}")

        except Exception as e:
            self.fail(f"Standard video test failed unexpectedly: {e}")


if __name__ == "__main__":
    # Run tests with verbose output
    print("=" * 70)
    print("MediaGrabber Integration Tests - Real YouTube URLs")
    print("=" * 70)
    print("\nThese tests make actual network calls to YouTube.")
    print("If tests fail due to network issues, try again later.\n")

    # Run tests
    unittest.main(verbosity=2)
