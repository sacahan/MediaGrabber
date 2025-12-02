#!/usr/bin/env python3
"""
快速測試腳本：驗證 pytubefix 是否可以成功下載 YouTube 影片
"""

import sys
from pathlib import Path

# 確保可以導入專案模組
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_pytubefix():
    """測試 pytubefix 下載"""
    try:
        from pytubefix import YouTube
        from pytubefix.cli import on_progress

        print("=" * 60)
        print("測試方案 1: pytubefix")
        print("=" * 60)

        # 測試 URL
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        output_dir = Path(__file__).parent / "downloads"
        output_dir.mkdir(exist_ok=True)

        print(f"\n📹 影片: {url}")
        print(f"📁 輸出: {output_dir.absolute()}\n")

        # 建立 YouTube 物件
        yt = YouTube(url, on_progress_callback=on_progress)

        print(f"✓ 標題: {yt.title}")
        print(f"✓ 長度: {yt.length} 秒")
        print(f"✓ 作者: {yt.author}")
        print(f"✓ 觀看次數: {yt.views:,}")

        # 下載音訊
        print("\n正在下載音訊...")
        audio_stream = yt.streams.get_audio_only()
        print(f"音訊串流: {audio_stream}")

        output_file = audio_stream.download(output_path=str(output_dir), mp3=True)

        file_size = Path(output_file).stat().st_size / (1024 * 1024)
        print(f"\n✅ 成功！檔案: {output_file}")
        print(f"✅ 大小: {file_size:.2f} MB")

        return True

    except ImportError:
        print("❌ pytubefix 未安裝")
        print("   執行: pip install pytubefix")
        return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ytdlp_alternatives():
    """測試 yt-dlp 替代配置"""
    try:
        from yt_dlp import YoutubeDL

        print("\n" + "=" * 60)
        print("測試方案 2: yt-dlp with alternative config")
        print("=" * 60)

        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        output_dir = Path(__file__).parent / "downloads"

        print(f"\n📹 影片: {url}")
        print(f"📁 輸出: {output_dir.absolute()}\n")

        # 使用 Android client 配置
        ydl_opts = {
            "quiet": False,
            "no_warnings": False,
            "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
            "format": "bestaudio/best",
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                    "player_skip": ["webpage"],
                }
            },
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"\n✅ 成功！標題: {info.get('title')}")
            return True

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主測試流程"""
    print("\n" + "🚀 " * 20)
    print("YouTube 下載替代方案測試")
    print("🚀 " * 20 + "\n")

    results = {}

    # 測試 pytubefix
    results["pytubefix"] = test_pytubefix()

    # 測試 yt-dlp 替代配置
    results["ytdlp_alt"] = test_ytdlp_alternatives()

    # 總結
    print("\n" + "=" * 60)
    print("測試結果總結")
    print("=" * 60)

    for method, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{method:20s} : {status}")

    # 檢查下載的檔案
    print("\n下載的檔案:")
    download_dir = Path(__file__).parent / "downloads"
    if download_dir.exists():
        files = list(download_dir.glob("*"))
        if files:
            for f in files:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  ✓ {f.name} ({size_mb:.2f} MB)")
        else:
            print("  ❌ 沒有找到檔案")

    print("\n" + "=" * 60)

    # 返回是否有至少一個方案成功
    return any(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
