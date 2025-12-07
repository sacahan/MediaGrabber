"""請求驗證器：為 API 層驗證請求並解析模式。

此模組負責：
1. 解析和驗證來自 API 的請求資料
2. 處理 cookies 的 base64 編解碼
3. 提供統一的錯誤訊息
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class DownloadRequest:
    """下載請求：從 API 解析的下載請求。

    屬性:
        url: 要下載的媒體 URL
        format: 請求的輸出格式（mp4/mp3/zip）
        cookies_base64: Base64 編碼的 cookies 資料（可選）
    """

    url: str  # 媒體 URL
    format: str  # 輸出格式
    cookies_base64: Optional[str] = None  # Base64 編碼的 cookies

    @classmethod
    def from_json(cls, data: dict) -> DownloadRequest:
        """從 JSON 解析請求：從 JSON 請求主體建立請求物件。

        Args:
            data: JSON 請求資料字典

        Returns:
            DownloadRequest 實例
        """
        return cls(
            url=data.get("url", ""),
            format=data.get("format", "mp4"),
            cookies_base64=data.get("cookiesBase64"),
        )

    def validate(self) -> tuple[bool, Optional[str]]:
        """驗證請求參數：檢查所有請求參數是否有效。

        驗證項目：
        - URL 是否提供
        - 格式是否在支援的清單中
        - Cookies 格式是否正確（如果提供）

        Returns:
            元組 (is_valid, error_message)
            - is_valid: 是否通過驗證
            - error_message: 錯誤訊息（如果驗證失敗）
        """
        if not self.url:
            return False, "url is required"
        if self.format not in ("mp4", "mp3", "zip"):
            return False, "format must be one of: mp4, mp3, zip"
        if self.cookies_base64:
            try:
                # 嘗試解碼並驗證 JSON 結構
                decoded = base64.b64decode(self.cookies_base64).decode("utf-8")
                json.loads(decoded)
            except (
                base64.binascii.Error,
                ValueError,
                UnicodeDecodeError,
            ) as e:
                return False, f"Invalid cookies format: {e}"
        return True, None

    def save_cookies_file(self, output_dir: Path) -> Optional[Path]:
        """Save cookies from base64 to temp file."""
        if not self.cookies_base64:
            return None

        try:
            decoded = base64.b64decode(self.cookies_base64).decode("utf-8")
            cookies_path = output_dir / "cookies.txt"
            cookies_path.write_text(decoded)
            return cookies_path
        except Exception:
            return None
