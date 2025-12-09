"""轉碼設定檔定義：定義主要和備用的轉碼預設。

此模組定義了影片轉碼的各種參數，基於 HandBrake 的 "Fast 1080p30" 預設。
包括解析度、位元率、檔案大小限制等。
轉碼過程強制轉換為 9:16 的手機標準格式（直豎格式），適合現代手機和社交媒體。
如果主要設定檔產生的檔案過大，會自動切換到備用設定檔。

HandBrake Fast 1080p30 預設參數對應：
- 視訊編碼器：H.264 (libx264)
- 解析度：1080x1920（主要）/ 720x1280（備用）
- 位元率：6000 kbps
- CRF：22 (品質因子)
- 幀率：30 fps
- 音訊：AAC 160 kbps 立體聲
- 預設：fast (編碼速度)
- 長寬比：9:16（強制，直豎格式）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple


@dataclass(slots=True)
class TranscodeProfile:
    """轉碼設定檔：描述單一轉碼設定的所有參數。

    使用優化的 x264 參數以支援線上播放。

    屬性:
        name: 設定檔名稱（mobile-primary 或 mobile-fallback）
        resolution: 影片解析度（寬度, 高度）
        video_bitrate_kbps: 影片位元率（kbps）
        audio_bitrate_kbps: 音訊位元率（kbps）
        max_filesize_mb: 最大檔案大小限制（MB）
        crf: 恆定品質因子（Constant Rate Factor, 0-51，值越小品質越好）
        x264_params: x264 編碼器自訂參數
        container: 容器格式（mp4 或 mp3）
    """

    name: Literal["mobile-primary", "mobile-fallback"]  # 設定檔名稱
    resolution: Tuple[int, int]  # 解析度 (width, height)
    video_bitrate_kbps: int  # 影片位元率
    audio_bitrate_kbps: int  # 音訊位元率
    max_filesize_mb: int  # 最大檔案大小
    crf: int  # 恆定品質因子
    x264_params: str  # x264 自訂參數
    container: Literal["mp4", "mp3"]  # 容器格式

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "resolution": self.resolution,
            "videoBitrateKbps": self.video_bitrate_kbps,
            "audioBitrateKbps": self.audio_bitrate_kbps,
            "maxFilesizeMb": self.max_filesize_mb,
            "crf": self.crf,
            "x264Params": self.x264_params,
            "container": self.container,
        }


@dataclass(slots=True)
class TranscodeProfilePair:
    """轉碼設定檔配對：包含主要和備用設定檔。

    當主要設定檔產生的檔案超過限制時，會自動降級到備用設定檔。
    """

    primary: TranscodeProfile
    fallback: TranscodeProfile

    def as_dict(self) -> dict:
        return {
            "primary": self.primary.as_dict(),
            "fallback": self.fallback.as_dict(),
        }


# 預設轉碼設定檔配置
# 使用優化的 x264 參數支援線上播放

# 主要設定檔：高品質（適合桌面和高端行動設備）
# 1080x1920 (9:16), 直豎格式，適合 Instagram Reels 和現代手機
# 注意：x264_params 不包含 crf (在 transcode_service 中單獨指定)
PROFILE_FAST_1080P30_PRIMARY = TranscodeProfile(
    name="mobile-primary",
    resolution=(1080, 1920),  # 1080x1920 (9:16 直豎)
    video_bitrate_kbps=15000,  # 視訊位元率
    audio_bitrate_kbps=160,  # AAC 立體聲
    max_filesize_mb=400,  # 檔案限制
    crf=22,  # 品質因子
    x264_params="vbv-bufsize=23438:vbv-maxrate=18750",
    container="mp4",
)

# 備用設定檔：低品質（適合低端行動設備或網路有限環境）
# 720x1280 (9:16), 直豎格式
PROFILE_FAST_1080P30_FALLBACK = TranscodeProfile(
    name="mobile-fallback",
    resolution=(720, 1280),  # 720x1280 (9:16 直豎)
    video_bitrate_kbps=8000,  # 降低 VBV 位元率
    audio_bitrate_kbps=128,  # 降低音訊位元率
    max_filesize_mb=250,  # 更小的檔案限制
    crf=28,  # 較低的品質
    x264_params="vbv-bufsize=12500:vbv-maxrate=10000",
    container="mp4",
)

# 預設配對（所有平台使用統一的 9:16 直豎格式）
DEFAULT_TRANSCODE_PROFILE = TranscodeProfilePair(
    primary=PROFILE_FAST_1080P30_PRIMARY,
    fallback=PROFILE_FAST_1080P30_FALLBACK,
)
