#!/usr/bin/env python3
"""
MediaGrabber CLI: download YouTube audio (MP3) or Facebook/Instagram video (MP4).
"""

import re
import time
import sys
from pathlib import Path
import argparse

from tqdm import tqdm
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, GeoRestrictedError


def _prepare_download(url: str, output_dir: Path):
    """Prepares for a download by creating the output directory and determining a safe filename.

    This function extracts the video title and sanitizes it to create a valid
    and readable filename. It replaces characters that are illegal in common
    file systems (like <, >, :, ", /, \, |, ?, *) with underscores. To prevent
    overly long filenames, which can cause issues on some operating systems,
    the sanitized title is truncated to a maximum of 50 characters.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Configure yt-dlp to only extract metadata without downloading the video.
    # 'quiet' and 'no_warnings' suppress console output from yt-dlp.
    # 'noplaylist' ensures only single video info is extracted, ignoring playlist parameters.
    meta_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True}
    with YoutubeDL(meta_opts) as ydl_meta:
        info = ydl_meta.extract_info(url, download=False)
    title = info.get('title', '')
    # Remove invalid characters and replace with underscore
    basename = re.sub(r'[<>:"/\\|?*]', '_', title)
    # Truncate to 50 characters if longer
    if len(basename) > 50:
        basename = basename[:50]
    return str(output_dir / f"{basename}.%(ext)s")


def download_and_extract_audio(url: str, output_dir: Path, progress_hook=None):
    """Download a YouTube video and extract audio as MP3 using yt-dlp and ffmpeg.

    Args:
        url (str): The URL of the video to download.
        output_dir (Path): The directory where the audio file will be saved.
        progress_hook (callable, optional): A callback function to report download progress.
                                            Used by the web GUI to update progress status.
    """
    # Determine the output template for the filename, ensuring it's safe and truncated.
    outtmpl = _prepare_download(url, output_dir)
    # If no external progress hook is provided (e.g., when running from CLI),
    # use a default tqdm-based progress bar for console output.
    if progress_hook is None:
        progress = {"pbar": None}

        def hook(d):
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if progress["pbar"] is None:
                    # Initialize tqdm progress bar on first download status update.
                    progress["pbar"] = tqdm(
                        total=total, unit="B", unit_scale=True, desc="Downloading"
                    )
                # Update the progress bar with the difference in downloaded bytes.
                progress["pbar"].update(d.get("downloaded_bytes", 0) - progress["pbar"].n)
            elif status == "finished":
                # Close the tqdm progress bar once download is complete.
                if progress["pbar"] is not None:
                    progress["pbar"].close()
                print("Download finished, extracting audio...")

    else:
        # Use the provided external progress hook (e.g., from Flask app).
        hook = progress_hook

    # yt-dlp options for audio extraction.
    # 'format': 'bestaudio/best' selects the best audio quality.
    # 'postprocessors' configures FFmpeg to extract audio and convert to MP3.
    # 'preferredquality': '192' sets the MP3 bitrate to 192kbps.
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_video_file(url: str, output_dir: Path, progress_hook=None):
    """Download a video (video + audio) and merge into MP4 using yt-dlp and ffmpeg.

    Args:
        url (str): The URL of the video to download.
        output_dir (Path): The directory where the video file will be saved.
        progress_hook (callable, optional): A callback function to report download progress.
                                            Used by the web GUI to update progress status.
    """
    # Determine the output template for the filename, ensuring it's safe and truncated.
    outtmpl = _prepare_download(url, output_dir)
    # If no external progress hook is provided (e.g., when running from CLI),
    # use a default tqdm-based progress bar for console output.
    if progress_hook is None:
        progress = {"pbar": None}

        def hook(d):
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if progress["pbar"] is None:
                    # Initialize tqdm progress bar on first download status update.
                    progress["pbar"] = tqdm(
                        total=total, unit="B", unit_scale=True, desc="Downloading"
                    )
                # Update the progress bar with the difference in downloaded bytes.
                progress["pbar"].update(d.get("downloaded_bytes", 0) - progress["pbar"].n)
            elif status == "finished":
                # Close the tqdm progress bar once download is complete.
                if progress["pbar"] is not None:
                    progress["pbar"].close()
                print("Download finished, merging video...")

    else:
        # Use the provided external progress hook (e.g., from Flask app).
        hook = progress_hook

    # yt-dlp options for video download and merging.
    # 'format': 'bestvideo+bestaudio' downloads best quality video and audio separately.
    # 'merge_output_format': 'mp4' ensures FFmpeg merges them into an MP4 container.
    # 'postprocessor_args' provides specific FFmpeg arguments for video encoding,
    # optimizing for compatibility and quality (e.g., H.264 codec, 30fps).
    ydl_opts = {
        "format": "bestvideo+bestaudio",
        "merge_output_format": "mp4",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "postprocessor_args": [
            "-c:v",
            "libx264",
            "-r",
            "30",
            "-x264-params",
            "level=4.0:ref=2:8x8dct=0:weightp=1:subme=6:vbv-bufsize=25000:vbv-maxrate=20000:rc-lookahead=30",
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def main():
    """Main function for the CLI application.

    Parses command-line arguments, sets up the output directory, and calls
    the appropriate download function based on user's format choice.
    Includes robust error handling for common yt-dlp issues.
    """
    parser = argparse.ArgumentParser(
        description="MediaGrabber CLI: download media as MP3 or MP4"
    )
    parser.add_argument(
        "url",
        help="Video URL (e.g., YouTube, Facebook, Instagram)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["mp3", "mp4"], default="mp3",
        help="Format to download: 'mp3' for audio, 'mp4' for video (default: mp3)",
    )
    parser.add_argument(
        "-o", "--output",
        default="../output", # Changed default output to a common 'output' directory outside backend
        help="Output directory (default: ../output)",
    )
    args = parser.parse_args()

    outdir = Path(args.output)
    try:
        if args.format == 'mp3':
            download_and_extract_audio(args.url, outdir)
            label = 'MP3'
        else:
            download_video_file(args.url, outdir)
            label = 'MP4'
        print(f"All done! {label} files are in: {outdir.resolve()}")
    # Catch specific yt-dlp errors to provide user-friendly messages.
    except GeoRestrictedError:
        print("Error: This video is not available in your region.", file=sys.stderr)
        sys.exit(1)
    except ExtractorError:
        print("Error: Could not extract video information. The URL may be invalid or unsupported.", file=sys.stderr)
        sys.exit(1)
    except DownloadError as e:
        print(f"Error: Download failed. {e}", file=sys.stderr)
        sys.exit(1)
    # Catch any other unexpected errors.
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

