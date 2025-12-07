"""進度狀態追蹤：跨 CLI 和 REST API 共用的進度遠測資料結構。

此模組定義了用於追蹤下載任務進度的資料結構，可用於即時更新
使用者界面或記錄詳細的進度資訊。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

# 進度狀態類型：描述任務當前的進度狀態
ProgressStatus = Literal[
    "queued",  # 已排隊：等待開始處理
    "downloading",  # 下載中：正在下載媒體
    "transcoding",  # 轉碼中：正在轉換格式
    "packaging",  # 封裝中：正在打包檔案
    "completed",  # 已完成：任務成功
    "failed",  # 已失敗：任務失敗
]


@dataclass(slots=True)
class ProgressState:
    """進度狀態：描述任務的即時進度資訊。

    此類別包含了追蹤任務執行進度所需的所有資訊，
    包括完成百分比、下載速度、預估剩餘時間等。

    屬性:
        job_id: 任務唯一識別碼
        status: 目前進度狀態
        stage: 當前處理階段描述
        percent: 完成百分比 (0.0-100.0)
        message: 進度訊息
        downloaded_bytes: 已下載的位元組數
        total_bytes: 總位元組數（如果已知）
        speed: 下載速度（位元組/秒）
        eta_seconds: 預估剩餘時間（秒）
        retry_after_seconds: 重試前等待時間（秒）
        attempts_remaining: 剩餘重試次數
        remediation: 補救建議（當出現問題時）
        timestamp: 進度更新的時間戳記
    """

    job_id: str  # 任務 ID
    status: ProgressStatus  # 進度狀態
    stage: str  # 處理階段
    percent: float  # 完成百分比
    message: str = ""  # 進度訊息
    downloaded_bytes: int = 0  # 已下載大小
    total_bytes: Optional[int] = None  # 總大小（可能未知）
    speed: Optional[float] = None  # 下載速度（bytes/s）
    eta_seconds: Optional[int] = None  # 預估剩餘時間
    retry_after_seconds: Optional[int] = None  # 重試等待時間
    attempts_remaining: Optional[int] = None  # 剩餘重試次數
    remediation: Optional[str] = None  # 補救建議
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )  # 時間戳記

    def clamp_percent(self) -> None:
        """限制百分比範圍：確保進度百分比在 0.0-100.0 之間。

        此方法防止進度百分比出現異常值（如負數或超過 100）。
        """
        self.percent = max(0.0, min(100.0, self.percent))

    def with_message(self, message: str) -> "ProgressState":
        """設定訊息：更新進度訊息並返回自身（支援鏈式呼叫）。

        Args:
            message: 新的進度訊息

        Returns:
            返回自身，支援鏈式呼叫
        """
        self.message = message
        return self
