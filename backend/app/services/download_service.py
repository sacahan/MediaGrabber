"""核心下載服務：處理 YouTube 和社交平台的媒體下載。

此服務是整個下載系統的核心，負責：
1. 協調 YouTube 和社交平台的下載
2. 管理重試策略和錯誤處理
3. 發布進度更新到進度匯流排
4. 支援自動重試和指數退避
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from ..models.download_job import DownloadJob, DownloadError
from ..models.progress_state import ProgressState
from ..services.retry_policy import RetryPolicy, RetryRemedy
from .progress_bus import ProgressBus


@dataclass(slots=True)
class DownloadResult:
    """下載結果：代表一次下載操作的結果。

    屬性:
        file_path: 下載檔案的完整路徑
        size_bytes: 檔案大小（位元組）
        duration_seconds: 下載持續時間（秒）
        error: 錯誤資訊（如果失敗）
    """

    file_path: Path  # 下載檔案路徑
    size_bytes: int  # 檔案大小
    duration_seconds: Optional[float] = None  # 下載時間
    error: Optional[DownloadError] = None  # 錯誤資訊


class DownloadService:
    """統一下載服務：為 YouTube 和社交平台提供統一的下載協調。

    此類別整合了不同平台的下載逻輯，提供統一的介面和錯誤處理。
    支援 YouTube（使用 pytubefix）和其他社交平台（使用 yt-dlp）。

    屬性:
        _bus: 進度匯流排，用於發布進度更新
        _retry_policy: 重試策略，管理失敗重試逻輯
    """

    def __init__(self, progress_bus: ProgressBus) -> None:
        """初始化下載服務。

        Args:
            progress_bus: 進度匯流排實例，用於發布進度更新
        """
        self._bus = progress_bus
        # 設定重試策略：最多 3 次重試，基礎延遲 1 秒
        self._retry_policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0)

    async def download_youtube(
        self,
        job: DownloadJob,
        url: str,
    ) -> DownloadResult:
        """下載 YouTube 影片：使用 pytubefix 庫下載 YouTube 影片。

        注意：目前實際的下載邏輯在 api/downloads.py 中使用 yt-dlp 實現。
        此方法是為未來的服務層架構重構預留的介面。

        pytubefix 是專門為 YouTube 最佳化的下載庫，提供更好的效能和穩定性。
        未來會整合到此處以提供統一的服務層介面。

        Args:
            job: 下載任務物件
            url: YouTube 影片的 URL

        Returns:
            下載結果，包含檔案路徑和大小
        """
        # 目前使用占位實現，實際下載邏輯在 api/downloads.py 的 _run_download 函數中
        # 使用 yt-dlp 進行下載和格式轉換
        await self._publish_progress(
            job, "downloading", "Initializing YouTube download...", 10.0
        )
        return DownloadResult(
            file_path=job.output_dir / "placeholder.mp4",
            size_bytes=0,
        )

    async def download_social(
        self,
        job: DownloadJob,
        url: str,
        cookies_path: Optional[Path] = None,
    ) -> DownloadResult:
        """下載社交平台影片：使用 yt-dlp 下載 Instagram/Facebook/X 影片。

        注意：目前實際的下載邏輯在 api/downloads.py 中實現。
        此方法是為未來的服務層架構重構預留的介面。

        yt-dlp 支援多種社交平台，並可使用 cookies 處理需要認證的內容。
        實際實現包含：
        - 自動平台檢測
        - Threads 平台的手動解析器（yt-dlp 尚不支援）
        - 其他平台使用 yt-dlp 處理
        - 自動格式選擇和轉換（MP4/MP3）

        Args:
            job: 下載任務物件
            url: 社交平台影片的 URL
            cookies_path: cookies 檔案路徑（可選），用於處理需要登入的內容

        Returns:
            下載結果，包含檔案路徑和大小
        """
        # 目前使用占位實現，實際下載邏輯在 api/downloads.py 的 _run_download 函數中
        # 包含完整的 yt-dlp 整合和 Threads 手動解析器
        await self._publish_progress(
            job, "downloading", "Initializing social media download...", 10.0
        )
        return DownloadResult(
            file_path=job.output_dir / "placeholder.mp4",
            size_bytes=0,
        )

    async def download_with_retry(
        self,
        job: DownloadJob,
        url: str,
        cookies_path: Optional[Path] = None,
    ) -> DownloadResult:
        """Download with exponential backoff retry."""

        async def do_download() -> DownloadResult:
            if job.platform == "youtube":
                return await self.download_youtube(job, url)
            else:
                return await self.download_social(job, url, cookies_path)

        async def on_retry(remedy: RetryRemedy) -> None:
            attempts_left = remedy.attempts_remaining
            if attempts_left is None:
                attempts_left = self._retry_policy.attempts_remaining
            attempts_left = max(0, attempts_left)
            countdown = remedy.retry_after_seconds or 1
            msg = f"Platform throttled, retrying in {countdown}s"
            job.retry_count = max(job.retry_count, self._retry_policy.attempt_count)
            await self._publish_progress(
                job,
                "downloading",
                msg,
                max(job.progress_percent, 5.0),
                retry_after_seconds=countdown,
                attempts_remaining=attempts_left,
                remediation=remedy.action or remedy.message,
            )

        try:
            result = await self._retry_policy.execute_with_retry(
                do_download, on_retry=on_retry
            )
            job.retry_count = max(0, self._retry_policy.attempt_count - 1)
            await self._publish_progress(
                job,
                "completed",
                "Download complete",
                100.0,
            )
            return result
        except Exception as exc:
            error = DownloadError(
                code=self._retry_policy.classify_error(exc).value,
                message=str(exc),
                remediation=self._retry_policy.remediation_message(),
            )
            job.retry_count = self._retry_policy.attempt_count
            await self._publish_progress(
                job,
                "failed",
                f"Download failed: {error.message}",
                job.progress_percent,
                remediation=error.remediation,
            )
            return DownloadResult(file_path=Path(), size_bytes=0, error=error)

    async def _publish_progress(
        self,
        job: DownloadJob,
        status: Literal[
            "downloading",
            "transcoding",
            "packaging",
            "failed",
            "completed",
        ],
        message: str,
        percent: float,
        *,
        retry_after_seconds: Optional[int] = None,
        attempts_remaining: Optional[int] = None,
        remediation: Optional[str] = None,
    ) -> None:
        """Publish progress update to bus and keep job percent in sync."""
        job.progress_percent = max(job.progress_percent, percent)
        state = ProgressState(
            job_id=job.job_id,
            status=status,  # type: ignore[arg-type]
            stage=message,
            percent=job.progress_percent,
            message=message,
            retry_after_seconds=retry_after_seconds,
            attempts_remaining=attempts_remaining,
            remediation=remediation,
        )
        self._bus.publish(state)

    @property
    def progress_percent(self) -> Optional[float]:
        """Get current progress percentage."""
        return None
