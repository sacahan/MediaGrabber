"""資料結構定義：描述下載/轉碼任務的生命週期。

此模組定義了下載任務的核心資料結構，包括:
- DownloadJob: 下載任務的完整描述
- DownloadError: 錯誤訊息結構
- DownloadArtifact: 產出檔案的描述
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

from .playlist_package import PlaylistItemResult
from .transcode_profile import TranscodeProfilePair

# 任務狀態類型：描述任務當前所處的階段
JobStatus = Literal[
    "pending",  # 等待中：任務已建立但尚未開始
    "queued",  # 已排隊：任務在佇列中等待執行
    "downloading",  # 下載中：正在從平台下載媒體
    "transcoding",  # 轉碼中：正在進行格式轉換
    "packaging",  # 封裝中：正在打包成最終格式
    "cleanup",  # 清理中：正在清理暫存檔案
    "completed",  # 已完成：任務成功完成
    "failed",  # 已失敗：任務執行失敗
]

# 任務階段類型：描述任務處理的主要階段
JobStage = Literal["init", "download", "transcoding", "packaging", "cleanup"]

# 產出類型：描述產生的檔案類型
ArtifactType = Literal["video", "audio", "archive"]  # 影片、音訊、壓縮檔


@dataclass(slots=True)
class DownloadError:
    """結構化錯誤資訊：用於在 CLI 和 REST API 之間傳遞錯誤訊息。

    屬性:
        code: 錯誤代碼，用於程式化識別錯誤類型
        message: 人類可讀的錯誤訊息
        remediation: 建議的補救措施（可選）
    """

    code: str  # 錯誤代碼，例如: "NETWORK_ERROR", "PLATFORM_THROTTLE"
    message: str  # 錯誤訊息，例如: "網路連線逾時"
    remediation: Optional[str] = None  # 補救建議，例如: "請檢查網路連線"


@dataclass(slots=True)
class DownloadArtifact:
    """下載產出檔案：代表任務執行過程中產生的檔案。

    此類別用於追蹤任務產生的所有檔案，包括影片、音訊、壓縮檔等。

    屬性:
        job_id: 所屬任務的唯一識別碼
        artifact_id: 產出檔案的唯一識別碼
        type: 產出類型（video/audio/archive）
        path: 檔案在檔案系統中的路徑
        size_bytes: 檔案大小（位元組）
        checksum: 檔案校驗和，用於驗證完整性（可選）
        compression_ratio: 壓縮率（可選），例如 0.7 表示壓縮至原大小的 70%
        expires_at: 檔案過期時間（可選），過期後可能被自動清理
    """

    job_id: str  # 所屬任務 ID
    artifact_id: str  # 產出檔案 ID
    type: ArtifactType  # 產出類型
    path: Path  # 檔案路徑
    size_bytes: int  # 檔案大小（位元組）
    checksum: Optional[str] = None  # 檔案校驗和（MD5/SHA256）
    compression_ratio: Optional[float] = None  # 壓縮率（0.0-1.0）
    expires_at: Optional[datetime] = None  # 過期時間

    def as_dict(self) -> dict:
        """將產出檔案資訊轉換為字典格式，用於 JSON 序列化。

        Returns:
            包含產出檔案所有資訊的字典，鍵名使用 camelCase 格式
        """
        return {
            "artifactId": self.artifact_id,
            "type": self.type,
            "path": str(self.path),
            "sizeBytes": self.size_bytes,
            "checksum": self.checksum,
            "compressionRatio": self.compression_ratio,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass(slots=True)
class DownloadJob:
    """下載任務：下載/轉碼請求的標準表示。

    此類別是整個系統的核心資料結構，描述了一個完整的媒體下載任務，
    包含來源、目標格式、處理設定、狀態追蹤等所有必要資訊。

    屬性:
        job_id: 任務唯一識別碼（UUID）
        source_url: 來源媒體的 URL
        platform: 平台類型（youtube/instagram/facebook/x）
        requested_format: 使用者請求的輸出格式（mp4/mp3/zip）
        download_backend: 使用的下載後端（pytubefix 用於 YouTube，yt-dlp 用於其他）
        profile: 轉碼設定檔（包含主要和備用設定）
        output_dir: 輸出目錄路徑
        status: 目前任務狀態
        stage: 目前處理階段
        requested_at: 任務建立時間（UTC）
        updated_at: 最後更新時間（UTC）
        error: 錯誤資訊（如果失敗）
        playlist_items: 播放清單項目結果（如果是播放清單）
        artifacts: 已產生的檔案清單
        retry_count: 重試次數計數
        queue_wait_seconds: 在佇列中等待的時間（秒）
        progress_percent: 目前進度百分比（0.0-100.0）
    """

    job_id: str  # 任務 ID（UUID 格式）
    source_url: str  # 來源 URL
    platform: Literal["youtube", "instagram", "facebook", "x"]  # 平台類型
    requested_format: Literal["mp4", "mp3", "zip"]  # 請求的輸出格式
    download_backend: Literal["pytubefix", "yt-dlp"]  # 下載後端
    profile: TranscodeProfilePair  # 轉碼設定檔配對
    output_dir: Path  # 輸出目錄
    status: JobStatus = "pending"  # 任務狀態（預設：等待中）
    stage: JobStage = "init"  # 處理階段（預設：初始化）
    requested_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )  # 請求時間
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )  # 更新時間
    error: Optional[DownloadError] = None  # 錯誤資訊
    playlist_items: Optional[List[PlaylistItemResult]] = None  # 播放清單項目
    artifacts: List[DownloadArtifact] = field(default_factory=list)  # 產出檔案清單
    retry_count: int = 0  # 重試次數
    queue_wait_seconds: Optional[float] = None  # 佇列等待時間
    progress_percent: float = 0.0  # 進度百分比

    def touch(self) -> None:
        """更新時間戳記：在修改任務後刷新 updated_at 時間戳記。

        此方法應在任何修改任務狀態的操作後呼叫，以保持時間戳記的正確性。
        """
        self.updated_at = datetime.now(timezone.utc)

    def set_status(self, status: JobStatus, stage: Optional[JobStage] = None) -> None:
        """設定任務狀態：更新任務的狀態和階段，並刷新時間戳記。

        Args:
            status: 新的任務狀態
            stage: 新的處理階段（可選）
        """
        self.status = status
        if stage:
            self.stage = stage
        self.touch()  # 更新時間戳記

    def record_error(self, error: DownloadError) -> None:
        """記錄錯誤：將任務標記為失敗並記錄錯誤資訊。

        Args:
            error: 錯誤資訊物件
        """
        self.error = error
        self.status = "failed"  # 將狀態設為失敗
        self.touch()  # 更新時間戳記

    def add_artifact(self, artifact: DownloadArtifact) -> None:
        """新增產出檔案：將新產生的檔案加入產出清單。

        Args:
            artifact: 產出檔案物件
        """
        self.artifacts.append(artifact)
        self.touch()  # 更新時間戳記

    def to_dict(self) -> dict:
        return {
            "jobId": self.job_id,
            "sourceUrl": self.source_url,
            "platform": self.platform,
            "requestedFormat": self.requested_format,
            "downloadBackend": self.download_backend,
            "profile": self.profile.as_dict(),
            "outputDir": str(self.output_dir),
            "status": self.status,
            "stage": self.stage,
            "requestedAt": self.requested_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "error": self.error.__dict__ if self.error else None,
            "playlistItems": [item.as_dict() for item in self.playlist_items]
            if self.playlist_items
            else None,
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "retryCount": self.retry_count,
            "queueWaitSeconds": self.queue_wait_seconds,
        }
