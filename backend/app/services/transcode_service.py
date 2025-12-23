"""Transcode service handling ffmpeg operations with queue management.

此模組實現了基於 HandBrake "Fast 1080p30" 預設的 ffmpeg 轉碼服務。
整合的轉碼參數包括：
- 視訊編碼器：H.264 (libx264)
- 解析度：1920x1080 (可自動縮放)
- 位元率：6000 kbps (CRF 22)
- 幀率：30 fps
- 音訊：AAC 立體聲 160 kbps
- 容器：MP4
- 預設：fast (兼顧速度和品質)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from ..models.download_job import DownloadJob, DownloadError
from ..models.transcode_profile import TranscodeProfilePair
from ..services.progress_bus import ProgressBus
from ..services.retry_policy import RetryPolicy, RetryRemedy
from ..services.transcode_queue import TranscodeQueue

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TranscodeResult:
    """Result of a transcode operation."""

    output_path: Path
    size_bytes: int
    compression_ratio: float = 0.0
    error: Optional[DownloadError] = None


class TranscodeService:
    """Handle ffmpeg-based transcoding with queue management."""

    def __init__(
        self,
        queue: TranscodeQueue,
        progress_bus: ProgressBus,
    ) -> None:
        self._queue = queue
        self._bus = progress_bus
        self._retry_policy = RetryPolicy(max_attempts=2, base_delay_seconds=1.0)

    async def transcode_primary(
        self,
        job: DownloadJob,
        input_path: Path,
        output_path: Path,
        profile: TranscodeProfilePair,
    ) -> TranscodeResult:
        """使用主要設定檔轉碼：執行 ffmpeg 轉碼，必要時降級到備用設定檔。

        注意：目前系統中的格式轉換主要由 yt-dlp 在下載階段完成。
        yt-dlp 內建使用 ffmpeg 進行以下操作：
        - MP4: 合併最佳視訊和音訊串流
        - MP3: 提取音訊並轉換為 MP3 格式

        此服務是為未來需要獨立轉碼操作（如壓縮、解析度調整）預留的。
        實際使用場景：
        - 播放清單打包前的批次轉碼
        - 檔案大小超過限制時的重新壓縮
        - 自訂轉碼設定檔的應用

        Args:
            job: 下載任務物件
            input_path: 輸入檔案路徑
            output_path: 輸出檔案路徑
            profile: 轉碼設定檔配對（主要和備用）

        Returns:
            轉碼結果，包含輸出路徑和壓縮比
        """

        async def do_transcode() -> TranscodeResult:
            # 發布進度更新
            await self._publish_progress(
                job, "transcoding", "Starting primary transcode...", 20.0
            )

            # 調用 ffmpeg 進行轉碼（基於 HandBrake Fast 1080p30 預設）
            try:
                result = await self._run_ffmpeg_transcode(
                    input_path, output_path, profile.primary
                )
                return result
            except Exception as exc:
                logger.error(f"[{job.job_id}] Primary transcode failed: {exc}")
                raise

        async def on_retry(remedy: RetryRemedy) -> None:
            msg = f"Transcode retry: {remedy.message}"
            await self._publish_progress(job, "transcoding", msg, 20.0)

        try:
            result = await self._retry_policy.execute_with_retry(
                do_transcode, on_retry=on_retry
            )

            # Check if result exceeds max filesize; if so, try fallback
            if result.size_bytes > profile.primary.max_filesize_mb * 1024 * 1024:
                result = await self.transcode_fallback(
                    job, input_path, output_path, profile
                )

            return result
        except Exception as exc:
            error = DownloadError(
                code=self._retry_policy.classify_error(exc).value,
                message=str(exc),
                remediation=self._retry_policy.remediation_message(),
            )
            return TranscodeResult(output_path=Path(), size_bytes=0, error=error)

    async def transcode_fallback(
        self,
        job: DownloadJob,
        input_path: Path,
        output_path: Path,
        profile: TranscodeProfilePair,
    ) -> TranscodeResult:
        """使用備用設定檔轉碼：當主要設定檔產生的檔案過大時使用。

        備用設定檔通常使用：
        - 較低的解析度
        - 較高的壓縮比（CRF 值）
        - 較低的位元率

        這確保最終檔案符合大小限制，適合在行動裝置上使用。

        Args:
            job: 下載任務物件
            input_path: 輸入檔案路徑
            output_path: 輸出檔案路徑
            profile: 轉碼設定檔配對

        Returns:
            轉碼結果
        """
        await self._publish_progress(
            job, "transcoding", "Trying fallback profile...", 40.0
        )
        # 使用備用設定檔進行轉碼
        try:
            result = await self._run_ffmpeg_transcode(
                input_path, output_path, profile.fallback
            )
            return result
        except Exception as exc:
            logger.error(f"[{job.job_id}] Fallback transcode failed: {exc}")
            raise

    async def _run_ffmpeg_transcode(
        self, input_path: Path, output_path: Path, profile
    ) -> TranscodeResult:
        """執行實際的 ffmpeg 轉碼命令。

        使用優化的 x264 參數以支援線上播放，包括：
        - 視訊編碼器：libx264 (H.264)
        - H.264 Profile：Baseline (最大兼容性)
        - H.264 Level：4.0 (支援所有手機設備)
        - x264 自訂參數：vbv-bufsize, vbv-maxrate (位元率控制)
        - 預設：medium (兼顧速度和品質)
        - 幀率：30 fps
        - 音訊編碼器：aac
        - 容器格式：MP4 + faststart

        Args:
            input_path: 輸入檔案路徑
            output_path: 輸出檔案路徑
            profile: 轉碼設定檔

        Returns:
            轉碼結果，包含輸出路徑、檔案大小和壓縮比
        """
        # 構建 ffmpeg 命令參數
        width, height = profile.resolution
        video_crf = profile.crf
        audio_bitrate = profile.audio_bitrate_kbps
        x264_params = profile.x264_params

        # 構建 x264 x-option 參數（不包含 crf，在 ffmpeg 參數中單獨指定）
        x264_option = f"{x264_params}"

        # 使用 x264 自訂參數的 ffmpeg 命令
        ffmpeg_cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            # 視訊編碼器和參數
            "-c:v",
            "libx264",
            "-profile:v",
            "baseline",  # H.264 Baseline Profile (最大兼容性)
            "-level",
            "4.0",  # H.264 Level 4.0
            "-preset",
            "medium",  # 編碼速度 (medium: 兼顧速度和品質)
            "-crf",
            str(video_crf),  # 恆定品質因子
            "-x264opts",
            x264_option,  # 自訂 x264 參數 (vbv-bufsize, vbv-maxrate)
            "-r",
            "30",  # 30 fps
            # 縮放設定（強制轉換為 9:16 手機直豎格式）
            # scale: 縮放至目標尺寸，使用 increase 以放大較小影片
            # crop: 從中央裁剪任何超出部分，確保精確的目標解析度
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            # 音訊編碼器和參數
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_bitrate}k",  # AAC 位元率
            "-ac",
            "2",  # 立體聲
            # 字幕
            "-c:s",
            "mov_text",
            # 其他選項
            "-movflags",
            "+faststart",  # 允許邊下載邊播放
            "-y",  # 覆蓋輸出檔案
            str(output_path),
        ]

        logger.info(
            f"Starting ffmpeg transcode: {input_path.name} -> {output_path.name}"
        )
        logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        logger.debug(
            f"H.264 settings: profile=baseline, level=4.0, crf={video_crf}, x264_params={x264_option}"
        )

        try:
            # 啟動 ffmpeg 子進程
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 監聽 ffmpeg 輸出並追蹤進度
            await self._monitor_ffmpeg_progress(process, input_path, output_path)

            # 等待進程完成
            returncode = await process.wait()
            if returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode("utf-8", errors="ignore")
                raise Exception(
                    f"ffmpeg failed with return code {returncode}: {error_msg}"
                )

            # 獲取輸出檔案大小
            if output_path.exists():
                output_size = output_path.stat().st_size
                input_size = input_path.stat().st_size
                compression_ratio = output_size / input_size if input_size > 0 else 0

                logger.info(
                    f"Transcode completed: {output_path.name} "
                    f"({output_size / 1024 / 1024:.2f} MB, "
                    f"compression ratio: {compression_ratio:.2%})"
                )

                return TranscodeResult(
                    output_path=output_path,
                    size_bytes=output_size,
                    compression_ratio=compression_ratio,
                )
            else:
                raise Exception("Output file not created")

        except asyncio.CancelledError:
            logger.warning(f"Transcode cancelled for {input_path.name}")
            raise
        except Exception as exc:
            logger.error(f"Transcode error: {exc}")
            # 清理失敗的輸出檔案
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up output file: {e}")
            raise

    async def _monitor_ffmpeg_progress(
        self, process: asyncio.subprocess.Process, input_path: Path, output_path: Path
    ) -> None:
        """監聽 ffmpeg 進程的輸出並追蹤轉碼進度。

        ffmpeg 在 stderr 上輸出進度資訊，格式如：
        frame=  150 fps=0.0 q=-1.0 Lsize=    2048kB time=00:00:05.00 bitrate=3355.3kbits/s speed=   3.3x

        Args:
            process: ffmpeg 子進程
            input_path: 輸入檔案路徑
            output_path: 輸出檔案路徑
        """
        if process.stderr is None:
            return

        # 嘗試獲取輸入檔案的總持續時間
        total_duration = await self._get_video_duration(input_path)

        while True:
            line = await process.stderr.readline()
            if not line:
                break

            line_str = line.decode("utf-8", errors="ignore").strip()
            if not line_str:
                continue

            # 解析進度資訊
            # 格式: time=00:05:30.50 (時:分:秒.毫秒)
            if "time=" in line_str:
                try:
                    time_str = line_str.split("time=")[1].split()[0]
                    current_time = self._parse_time(time_str)

                    if total_duration > 0:
                        progress_percent = min(
                            95, (current_time / total_duration) * 100
                        )
                        logger.debug(
                            f"Transcode progress: {progress_percent:.1f}% "
                            f"({current_time:.1f}s / {total_duration:.1f}s)"
                        )
                except Exception as e:
                    logger.debug(f"Error parsing ffmpeg progress: {e}")

    @staticmethod
    async def _get_video_duration(video_path: Path) -> float:
        """使用 ffprobe 獲取影片持續時間（秒）。

        Args:
            video_path: 影片檔案路徑

        Returns:
            影片持續時間（秒），如果無法獲取則返回 0
        """
        try:
            # 嘗試使用 ffprobe 獲取持續時間
            process = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1:noinfer_type=1",
                str(video_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await process.communicate()
            duration_str = stdout.decode("utf-8", errors="ignore").strip()
            if duration_str:
                return float(duration_str)
        except Exception as e:
            logger.debug(f"Failed to get video duration with ffprobe: {e}")

        return 0

    @staticmethod
    def _parse_time(time_str: str) -> float:
        """解析 ffmpeg 時間格式 (HH:MM:SS.ms) 為秒數。

        Args:
            time_str: 時間字串，如 "00:05:30.50"

        Returns:
            秒數
        """
        try:
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return 0

    async def transcode_with_queue(
        self,
        job: DownloadJob,
        input_path: Path,
        output_path: Path,
        profile: TranscodeProfilePair,
    ) -> TranscodeResult:
        """Queue the transcode job and execute with bounded concurrency."""

        async def work() -> TranscodeResult:
            return await self.transcode_primary(job, input_path, output_path, profile)

        async with self._queue.worker_slot():
            return await work()

    async def _publish_progress(
        self,
        job: DownloadJob,
        status: Literal["transcoding"],
        message: str,
        percent: float,
    ) -> None:
        """Publish progress to bus."""
        from ..models.progress_state import ProgressState

        state = ProgressState(
            job_id=job.job_id,
            status=status,  # type: ignore
            stage=message,
            percent=percent,
            message=message,
        )
        self._bus.publish(state)
