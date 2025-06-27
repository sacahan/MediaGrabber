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
    """Prepares for a download by creating the output directory and determining a safe filename."""
    output_dir.mkdir(parents=True, exist_ok=True)
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
    """
    Download a YouTube video and extract audio as MP3 using yt-dlp and ffmpeg.
    """
    outtmpl = _prepare_download(url, output_dir)
    if progress_hook is None:
        progress = {"pbar": None}

        def hook(d):
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if progress["pbar"] is None:
                    progress["pbar"] = tqdm(
                        total=total, unit="B", unit_scale=True, desc="Downloading"
                    )
                progress["pbar"].update(d.get("downloaded_bytes", 0) - progress["pbar"].n)
            elif status == "finished":
                if progress["pbar"] is not None:
                    progress["pbar"].close()
                print("Download finished, extracting audio...")

    else:
        hook = progress_hook

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
    """
    Download a video (video + audio) and merge into MP4 using yt-dlp and ffmpeg.
    """
    outtmpl = _prepare_download(url, output_dir)
    if progress_hook is None:
        progress = {"pbar": None}

        def hook(d):
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if progress["pbar"] is None:
                    progress["pbar"] = tqdm(
                        total=total, unit="B", unit_scale=True, desc="Downloading"
                    )
                progress["pbar"].update(d.get("downloaded_bytes", 0) - progress["pbar"].n)
            elif status == "finished":
                if progress["pbar"] is not None:
                    progress["pbar"].close()
                print("Download finished, merging video...")

    else:
        hook = progress_hook

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
        default="output",
        help="Output directory (default: ./output)",
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
    except GeoRestrictedError:
        print("Error: This video is not available in your region.", file=sys.stderr)
        sys.exit(1)
    except ExtractorError:
        print("Error: Could not extract video information. The URL may be invalid or unsupported.", file=sys.stderr)
        sys.exit(1)
    except DownloadError as e:
        print(f"Error: Download failed. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
