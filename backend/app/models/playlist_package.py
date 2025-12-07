"""播放清單封裝結果：描述播放清單打包結果的資料結構。

當使用者下載播放清單時，每個項目都會分別處理，最後打包成 ZIP 檔。
此模組定義了用於追蹤每個項目的處理結果。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(slots=True)
class PlaylistItemResult:
    """播放清單項目結果：代表播放清單中單個項目的處理結果。

    屬性:
        index: 項目在播放清單中的索引位置
        title: 項目標題
        status: 處理狀態（completed 或 failed）
        artifact_path: 產出檔案路徑（如果成功）
        error_code: 錯誤代碼（如果失敗）
        error_message: 錯誤訊息（如果失敗）
        remediation: 補救建議（如果失敗）
    """

    index: int  # 項目索引
    title: str  # 項目標題
    status: str  # 狀態（completed/failed）
    artifact_path: Optional[Path] = None  # 產出檔案路徑
    error_code: Optional[str] = None  # 錯誤代碼
    error_message: Optional[str] = None  # 錯誤訊息
    remediation: Optional[str] = None  # 補救建議

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "status": self.status,
            "artifactPath": str(self.artifact_path) if self.artifact_path else None,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "remediation": self.remediation,
        }


@dataclass(slots=True)
class PlaylistPackage:
    """Aggregates playlist-wide packaging details including summaries."""

    job_id: str
    zip_path: Optional[Path] = None
    success_items: List[PlaylistItemResult] = field(default_factory=list)
    failed_items: List[PlaylistItemResult] = field(default_factory=list)

    def add_result(self, result: PlaylistItemResult) -> None:
        bucket = (
            self.success_items if result.status == "completed" else self.failed_items
        )
        bucket.append(result)

    def as_summary(self) -> dict:
        return {
            "jobId": self.job_id,
            "zipPath": str(self.zip_path) if self.zip_path else None,
            "successItems": [item.as_dict() for item in self.success_items],
            "failedItems": [item.as_dict() for item in self.failed_items],
        }
