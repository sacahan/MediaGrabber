"""重試策略：指數退避 + 錯誤分類，用於增強下載/轉碼的穩定性。

此模組實現了智能的重試策略，包括：
1. 指數退避：每次重試的等待時間指數增長
2. 錯誤分類：根據錯誤類型採取不同的重試策略
3. 補救建議：為使用者提供明確的解決方案
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")


class ErrorCategory(Enum):
    """錯誤分類：為重試逻輯將錯誤分類。

    不同類型的錯誤會採用不同的重試策略：
    - 暫時性錯誤：短時間內重試
    - 平台限流：需要較長的等待時間
    - 永久性錯誤：不應重試
    """

    TRANSIENT_NETWORK = "transient_network"  # 暫時性網路問題，例如：逾時、429 錯誤
    PLATFORM_THROTTLE = "platform_throttle"  # 平台明確的速率限制
    AUTH_FAILURE = "auth_failure"  # 認證失敗，例如：cookies 或憑證問題
    MISSING_DEPENDENCY = "missing_dependency"  # 缺少依賴，例如：ffmpeg 未安裝
    IO_ERROR = "io_error"  # I/O 錯誤，例如：磁碟已滿、權限不足
    PERMANENT = "permanent"  # 永久性錯誤，例如：影片不存在、帳號被封鎖


@dataclass(slots=True)
class RetryRemedy:
    """Structured remediation advice for a failed operation."""

    category: ErrorCategory
    message: str
    retry_after_seconds: Optional[int] = None
    attempts_remaining: int = 0
    action: Optional[str] = None  # e.g. "clear disk space", "check cookies"


class RetryPolicy:
    """重試策略：指數退避配合基於分類的退避乘數。

    此類別實現了智能重試策略：
    - 指數退避：等待時間每次翻倍（2^attempt）
    - 分類加權：平台限流等特定錯誤使用更長的等待時間
    - 最大延遲限制：防止等待時間過長

    屬性:
        _max_attempts: 最大重試次數
        _base_delay: 基礎延遲時間（秒）
        _max_delay: 最大延遲時間（秒）
        _clock: 時鐘函式（主要用於測試）
        _attempt_count: 目前嘗試次數
        _last_error: 最後一次的錯誤
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        """初始化重試策略。

        Args:
            max_attempts: 最大重試次數（預設 3 次）
            base_delay_seconds: 基礎延遲時間（預設 1 秒）
            max_delay_seconds: 最大延遲時間（預設 60 秒）
            clock: 自定義時鐘函式（可選，主要用於測試）

        Raises:
            ValueError: 如果 max_attempts < 1
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._max_attempts = max_attempts
        self._base_delay = base_delay_seconds
        self._max_delay = max_delay_seconds
        self._clock = clock or __import__("time").time
        self._attempt_count = 0
        self._last_error: Optional[Exception] = None

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def attempt_count(self) -> int:
        return self._attempt_count

    @property
    def attempts_remaining(self) -> int:
        return max(0, self._max_attempts - self._attempt_count)

    def classify_error(self, exc: Exception) -> ErrorCategory:
        """Map exception types to retry categories."""
        exc_type = type(exc).__name__
        exc_str = str(exc).lower()

        # Network timeouts
        if "timeout" in exc_str or exc_type == "TimeoutError":
            return ErrorCategory.TRANSIENT_NETWORK
        # Rate limiting
        if "429" in exc_str or "too many requests" in exc_str:
            return ErrorCategory.PLATFORM_THROTTLE
        # Authentication
        if (
            "unauthorized" in exc_str
            or "forbidden" in exc_str
            or "auth" in exc_str
            or exc_type == "PermissionError"
        ):
            return ErrorCategory.AUTH_FAILURE
        # Missing dependencies
        if (
            "not found" in exc_str
            or "no such file" in exc_str
            and "ffmpeg" in exc_str.lower()
        ):
            return ErrorCategory.MISSING_DEPENDENCY
        # IO errors
        if (
            "disk" in exc_str
            or "no space" in exc_str
            or exc_type in ("OSError", "IOError")
        ):
            return ErrorCategory.IO_ERROR
        # Assume permanent
        return ErrorCategory.PERMANENT

    def calculate_backoff(self, attempt: int, category: ErrorCategory) -> float:
        """Compute backoff seconds based on attempt count and error category."""
        # Platform throttles back off longer
        multiplier = 2.0 if category == ErrorCategory.PLATFORM_THROTTLE else 1.0
        delay = self._base_delay * (2 ** (attempt - 1)) * multiplier
        return min(delay, self._max_delay)

    async def execute_with_retry(
        self,
        work: Callable[[], Awaitable[T]],
        on_retry: Optional[Callable[[RetryRemedy], Awaitable[None]]] = None,
    ) -> T:
        """Execute work with exponential backoff on failure."""
        for attempt in range(1, self._max_attempts + 1):
            self._attempt_count = attempt
            try:
                return await work()
            except Exception as exc:
                self._last_error = exc
                if attempt >= self._max_attempts:
                    raise
                category = self.classify_error(exc)
                backoff = self.calculate_backoff(attempt, category)
                remedy = RetryRemedy(
                    category=category,
                    message=str(exc),
                    retry_after_seconds=int(backoff),
                    attempts_remaining=self.attempts_remaining - 1,
                    action=self._suggest_action(category),
                )
                if on_retry:
                    await on_retry(remedy)
                await asyncio.sleep(backoff)
        raise RuntimeError("Retry exhausted (unreachable)")

    @staticmethod
    def _suggest_action(category: ErrorCategory) -> Optional[str]:
        """Provide user-facing suggestions for recovery."""
        suggestions = {
            ErrorCategory.TRANSIENT_NETWORK: "Check your network connection and try again",
            ErrorCategory.PLATFORM_THROTTLE: "Platform rate-limited; will retry automatically",
            ErrorCategory.AUTH_FAILURE: "Check cookies or login credentials",
            ErrorCategory.MISSING_DEPENDENCY: "Ensure ffmpeg is installed and in PATH",
            ErrorCategory.IO_ERROR: "Check available disk space and try clearing temp files",
        }
        return suggestions.get(category)

    def remediation_message(self) -> Optional[str]:
        """Construct a remediation message for the last error."""
        if not self._last_error:
            return None
        category = self.classify_error(self._last_error)
        action = self._suggest_action(category)
        return action or f"Error: {self._last_error}"
