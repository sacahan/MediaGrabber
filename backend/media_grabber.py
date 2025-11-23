#!/usr/bin/env python3
"""
MediaGrabber CLI: download YouTube audio (MP3) or Facebook/Instagram video (MP4).
"""

import re
import sys
from pathlib import Path
import argparse

from tqdm import tqdm
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError, GeoRestrictedError


def _prepare_download(url: str, output_dir: Path):
    """Prepares for a download by creating the output directory and determining a safe filename.

    This function extracts the video title and sanitizes it to create a valid
    filename.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # Configure yt-dlp to only extract metadata without downloading the video.
    # 'quiet' and 'no_warnings' suppress console output from yt-dlp.
    # 'noplaylist' ensures only single video info is extracted, ignoring playlist
    # parameters.
    # IMPORTANT: Do NOT specify 'format' when using download=False
    # This prevents yt-dlp from validating format availability
    meta_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with YoutubeDL(meta_opts) as ydl_meta:
        info = ydl_meta.extract_info(url, download=False)
    title = info.get("title", "")
    # Remove invalid characters and replace with underscore
    basename = re.sub(r'[<>:"/\\|?*]', "_", title)  # Fixed invalid escape sequence
    # Truncate to 50 characters if longer
    if len(basename) > 50:
        basename = basename[:50]
    return str(output_dir / f"{basename}.%(ext)s")


def download_and_extract_audio(
    url: str, output_dir: Path, progress_hook=None, cookiefile: str = None
):
    """Download a YouTube video and extract audio as MP3 using yt-dlp and ffmpeg.

    Args:
        url (str): The URL of the video to download.
        output_dir (Path): The directory where the audio file will be saved.
        progress_hook (callable, optional): A callback function to report
            download progress. Used by the web GUI to update progress status.
        cookiefile (str, optional): Path to a cookie file.
    """
    # Determine the output template for the filename, ensuring it's safe and
    # truncated.
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
                progress["pbar"].update(
                    d.get("downloaded_bytes", 0) - progress["pbar"].n
                )
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
        # 解決 HTTP 403 Forbidden 錯誤
        # 添加現代的 User-Agent 避免被 YouTube 認定為機器人
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # 為 Instagram 添加必要的 HTTP 頭部
        "http_headers": {
            "Referer": "https://www.instagram.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        },
        # 添加延遲避免頻繁請求被封
        "socket_timeout": 30,
        # 嘗試使用瀏覽器 Cookies（需要本地有 Chrome/Firefox）
        "cookiesfrombrowser": ("chrome",),
        # 跳過不可用的片段
        "skip_unavailable_fragments": True,
        # Instagram 特定選項
        "extractor_args": {"instagram": {"fetch_all_comments": False}},
    }
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_video_file(
    url: str, output_dir: Path, progress_hook=None, cookiefile: str = None
):
    """Download a video (video + audio) and merge into MP4 using yt-dlp and ffmpeg.

    Args:
        url (str): The URL of the video to download.
        output_dir (Path): The directory where the video file will be saved.
        progress_hook (callable, optional): A callback function to report
            download progress. Used by the web GUI to update progress status.
        cookiefile (str, optional): Path to a cookie file.
    """
    # Determine the output template for the filename, ensuring it's safe and
    # truncated.
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
                progress["pbar"].update(
                    d.get("downloaded_bytes", 0) - progress["pbar"].n
                )
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
        # 解決 HTTP 403 Forbidden 錯誤
        # 添加現代的 User-Agent 避免被 YouTube 認定為機器人
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # 為 Instagram 添加必要的 HTTP 頭部
        "http_headers": {
            "Referer": "https://www.instagram.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        },
        # 添加延遲避免頻繁請求被封
        "socket_timeout": 30,
        # 嘗試使用瀏覽器 Cookies（需要本地有 Chrome/Firefox）
        "cookiesfrombrowser": ("chrome",),
        # 跳過不可用的片段
        "skip_unavailable_fragments": True,
        # Instagram 特定選項
        "extractor_args": {"instagram": {"fetch_all_comments": False}},
    }
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

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
        "-f",
        "--format",
        choices=["mp3", "mp4"],
        default="mp3",
        help="Format to download: 'mp3' for audio, 'mp4' for video (default: mp3)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="../output",  # Changed default output to a common 'output' directory outside backend
        help="Output directory (default: ../output)",
    )
    parser.add_argument(
        "-c",
        "--cookie",
        help="Cookie file to use for authentication",
    )
    args = parser.parse_args()

    outdir = Path(args.output)
    try:
        if args.format == "mp3":
            download_and_extract_audio(args.url, outdir, cookiefile=args.cookie)
            label = "MP3"
        else:
            download_video_file(args.url, outdir, cookiefile=args.cookie)
            label = "MP4"
        print(f"All done! {label} files are in: {outdir.resolve()}")
    # Catch specific yt-dlp errors to provide user-friendly messages.
    except GeoRestrictedError:
        print("Error: This video is not available in your region.", file=sys.stderr)
        sys.exit(1)
    except ExtractorError:
        print(
            "Error: Could not extract video information. The URL may be invalid or unsupported.",
            file=sys.stderr,
        )
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
