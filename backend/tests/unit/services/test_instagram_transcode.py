#!/usr/bin/env python3
"""測試 Instagram 下載 + 轉碼完整流程。

此腳本演示：
1. 從 Instagram Reel 下載視訊
2. 使用新的 TranscodeService 轉碼
3. 驗證輸出檔案的手機兼容性
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加 backend 到路徑
sys.path.insert(0, str(Path(__file__).parent))

from app.services.download_service import DownloadService
from app.models.transcode_profile import DEFAULT_TRANSCODE_PROFILE
from app.services.transcode_queue import TranscodeQueue
from app.services.progress_bus import ProgressBus
from app.services.transcode_service import TranscodeService
from app.models.download_job import DownloadJob


async def test_instagram_with_transcode():
    """測試完整的 Instagram 下載 + 轉碼流程。"""

    # 設定輸出目錄
    output_dir = Path("/tmp/instagram_transcode_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("📱 Instagram Reel 下載 + 轉碼測試")
    print("=" * 80)

    # Instagram URL
    instagram_url = "https://www.instagram.com/reel/DPthOqAkU3Y/?utm_source=ig_web_copy_link&igsh=NTc4MTIwNjQ2YQ=="

    print(f"\n🔗 URL: {instagram_url}")
    print(f"📁 輸出目錄: {output_dir}")

    try:
        # Step 1: 下載
        print("\n" + "=" * 80)
        print("Step 1: 從 Instagram 下載視訊")
        print("=" * 80)

        bus = ProgressBus(ttl_seconds=3600)
        download_service = DownloadService(bus)

        # 建立測試工作
        job = DownloadJob(
            job_id=f"test-{datetime.now().timestamp()}",
            source_url=instagram_url,
            platform="instagram",
            requested_format="mp4",
            download_backend="yt-dlp",
            profile=DEFAULT_TRANSCODE_PROFILE,
            output_dir=output_dir,
        )

        # 執行下載 (假設 yt-dlp 已安裝)
        try:
            result = await download_service.download(job)

            if result.error:
                print(f"❌ 下載失敗: {result.error.message}")
                return False

            downloaded_path = result.path
            print(f"✅ 下載完成: {downloaded_path}")
            print(f"   檔案大小: {downloaded_path.stat().st_size / 1024 / 1024:.2f} MB")

        except Exception as e:
            print(f"⚠️ 下載可能失敗或 yt-dlp 不可用: {e}")
            print("   跳過下載步驟，使用現有檔案進行轉碼測試")

            # 使用現有檔案進行測試
            test_files = list(output_dir.glob("*.mp4"))
            if not test_files:
                print("❌ 找不到測試檔案")
                return False
            downloaded_path = test_files[0]
            print(f"   使用現有檔案: {downloaded_path}")

        # Step 2: 轉碼
        print("\n" + "=" * 80)
        print("Step 2: 使用 TranscodeService 轉碼")
        print("=" * 80)

        output_path = output_dir / f"transcoded_{datetime.now().timestamp()}.mp4"

        # 初始化轉碼服務
        queue = TranscodeQueue(max_workers=1)
        transcode_bus = ProgressBus(ttl_seconds=3600)
        transcode_service = TranscodeService(queue, transcode_bus)

        print("⏳ 轉碼中...")
        print(f"   輸入: {downloaded_path.name}")
        print(f"   輸出: {output_path.name}")

        result = await transcode_service.transcode_primary(
            job, downloaded_path, output_path, DEFAULT_TRANSCODE_PROFILE
        )

        if result.error:
            print(f"❌ 轉碼失敗: {result.error.message}")
            return False

        print("✅ 轉碼完成!")
        print(f"   檔案大小: {result.size_bytes / 1024 / 1024:.2f} MB")
        print(f"   壓縮率: {result.compression_ratio:.2%}")

        # Step 3: 驗證轉碼結果
        print("\n" + "=" * 80)
        print("Step 3: 驗證手機兼容性")
        print("=" * 80)

        import subprocess

        # 使用 ffprobe 檢查編碼參數
        try:
            probe_result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,profile,level,width,height,r_frame_rate",
                    "-of",
                    "csv=p=0",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            codec_info = probe_result.stdout.strip()
            print(f"編碼檢查結果:\n  {codec_info}")

            # 驗證關鍵參數
            if "h264" in codec_info or "H.264" in codec_info:
                print("✅ 視訊編碼: H.264 ✓")
            else:
                print("❌ 視訊編碼: 非 H.264")

            if "Baseline" in codec_info or "Constrained Baseline" in codec_info:
                print("✅ Profile: Baseline ✓")
            else:
                print("⚠️  Profile: 可能不是 Baseline")

        except Exception as e:
            print(f"⚠️ 無法驗證編碼參數: {e}")

        print("\n" + "=" * 80)
        print("✨ 轉碼測試完成!")
        print("=" * 80)
        print("\n📁 轉碼後檔案位置:")
        print(f"   {output_path}")
        print("\n💡 建議:")
        print("   1. 複製此檔案到手機進行播放測試")
        print("   2. 嘗試快進、倒轉等功能")
        print("   3. 測試不同的播放器 (系統、VLC 等)")

        return True

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_instagram_with_transcode())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  測試已中止")
        sys.exit(1)
