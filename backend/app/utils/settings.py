"""應用設定加載器：從環境變數加載應用設定。

此模組提供了一個統一的方式來管理應用程式配置，
所有配置均從環境變數讀取，並提供合理的預設值。
支援快取以提高效能。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppSettings:
    """應用設定：不可變的應用配置物件。

    屬性:
        max_transcode_workers: 轉碼的最大並發 worker 數
        output_dir: 輸出檔案的根目錄
        progress_ttl_seconds: 進度狀態的生存時間（秒）
    """

    max_transcode_workers: int  # 最大轉碼 worker 數
    output_dir: Path  # 輸出目錄
    progress_ttl_seconds: int  # 進度 TTL（秒）


def _read_int(name: str, default: int, minimum: int = 1) -> int:
    """讀取整數環境變數：從環境變數讀取整數值並驗證。

    Args:
        name: 環境變數名稱
        default: 預設值（如果環境變數未設定）
        minimum: 最小允許值（預設 1）

    Returns:
        解析後的整數值

    Raises:
        ValueError: 如果值無法解析為整數或小於最小值
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    """加載設定：從環境變數加載所有應用設定。

    支援的環境變數：
    - MG_MAX_TRANSCODE_WORKERS: 最大轉碼 worker 數（預設 2）
    - MG_PROGRESS_TTL_SECONDS: 進度 TTL（預設 300 秒）
    - MG_OUTPUT_DIR: 輸出目錄（預設 "output"）

    此函式使用 lru_cache 快取，同一進程中只會加載一次。

    Returns:
        AppSettings 實例
    """
    max_workers = _read_int("MG_MAX_TRANSCODE_WORKERS", default=2, minimum=1)
    ttl_seconds = _read_int("MG_PROGRESS_TTL_SECONDS", default=300, minimum=60)
    output_dir = Path(os.environ.get("MG_OUTPUT_DIR", "output")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)  # 確保目錄存在
    return AppSettings(
        max_transcode_workers=max_workers,
        output_dir=output_dir,
        progress_ttl_seconds=ttl_seconds,
    )


def reset_settings_cache() -> None:
    """重設設定快取：清除快取的設定（主要用於測試）。

    此函式清除 load_settings 的 lru_cache，使下次呼叫時重新讀取環境變數。
    主要用於單元測試中更改環境變數後重新加載設定。
    """
    load_settings.cache_clear()
