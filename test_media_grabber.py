
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from media_grabber import download_and_extract_audio, download_video_file, _prepare_download

class MediaGrabberTests(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('media_grabber.YoutubeDL')
    def test_prepare_download_safe_title(self, mock_youtube_dl):
        # Mock the behavior of YoutubeDL
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {'title': 'A Safe Title'}
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        # Call the function
        output_dir = Path(self.test_dir)
        outtmpl = _prepare_download('fake_url', output_dir)

        # Assertions
        self.assertIn('A Safe Title.%(ext)s', outtmpl)
        mock_instance.extract_info.assert_called_with('fake_url', download=False)

    @patch('media_grabber.YoutubeDL')
    def test_prepare_download_unsafe_title(self, mock_youtube_dl):
        # Mock the behavior of YoutubeDL
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {'title': 'A Title With/\Invalid Chars'}
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        # Call the function
        output_dir = Path(self.test_dir)
        outtmpl = _prepare_download('fake_url', output_dir)

        # Assertions
        self.assertIn('A Title With__Invalid Chars', outtmpl)

    @patch('media_grabber.YoutubeDL')
    def test_prepare_download_long_and_unsafe_title(self, mock_youtube_dl):
        # Mock the behavior of YoutubeDL
        mock_instance = MagicMock()
        long_unsafe_title = "This is a very long title with some /\\:?*invalid characters and it should be truncated to 50 characters."
        mock_instance.extract_info.return_value = {'title': long_unsafe_title}
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        # Call the function
        output_dir = Path(self.test_dir)
        outtmpl = _prepare_download('fake_url', output_dir)

        # Assertions
        # Check if invalid characters are replaced and truncated
        actual_basename = Path(outtmpl).stem
        expected_basename = "This is a very long title with some _____invalid c"
        self.assertEqual(actual_basename, expected_basename)
        self.assertEqual(len(actual_basename), 50)

    @patch('media_grabber.YoutubeDL')
    def test_download_and_extract_audio(self, mock_youtube_dl):
        # Mock the behavior of YoutubeDL
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {'title': 'audio_test'}
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        # Call the function
        output_dir = Path(self.test_dir)
        download_and_extract_audio('fake_url', output_dir, progress_hook=lambda d: None)

        # Assertions
        self.assertEqual(mock_youtube_dl.call_count, 2)
        # The first call is in _prepare_download, the second is the actual download.
        # The arguments are (ydl_opts_dict,) so access args[0]
        ydl_opts = mock_youtube_dl.call_args_list[1].args[0]
        self.assertIn('FFmpegExtractAudio', str(ydl_opts['postprocessors']))
        self.assertIn('mp3', str(ydl_opts['postprocessors']))

    @patch('media_grabber.YoutubeDL')
    def test_download_video_file(self, mock_youtube_dl):
        # Mock the behavior of YoutubeDL
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {'title': 'video_test'}
        mock_youtube_dl.return_value.__enter__.return_value = mock_instance

        # Call the function
        output_dir = Path(self.test_dir)
        download_video_file('fake_url', output_dir, progress_hook=lambda d: None)

        # Assertions
        self.assertEqual(mock_youtube_dl.call_count, 2)
        # The arguments are (ydl_opts_dict,) so access args[0]
        ydl_opts = mock_youtube_dl.call_args_list[1].args[0]
        self.assertEqual(ydl_opts['merge_output_format'], 'mp4')

if __name__ == '__main__':
    unittest.main()
