"""Remediation service for generating user-friendly error messages and recovery actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCode(Enum):
    """Error classification codes."""

    NETWORK = "network_error"
    AUTH = "auth_error"
    DISK = "disk_error"
    FFMPEG = "ffmpeg_error"
    THROTTLE = "throttle_error"
    COOKIE = "cookie_error"
    UNKNOWN = "unknown_error"


@dataclass(slots=True)
class RemediationAdvice:
    """Structured remediation advice for errors."""

    error_code: ErrorCode
    message: str
    action: str
    severity: str  # "info", "warning", "error"


class RemediationService:
    """Generate remediation advice for various error conditions."""

    _ERROR_MESSAGES = {
        ErrorCode.NETWORK: {
            "message": "Network error occurred during download",
            "action": "Check your internet connection and try again",
            "severity": "warning",
        },
        ErrorCode.AUTH: {
            "message": "Authentication failed (invalid credentials or cookies)",
            "action": "Verify cookies file format or regenerate authentication",
            "severity": "error",
        },
        ErrorCode.DISK: {
            "message": "Insufficient disk space for output",
            "action": "Free up disk space and try again",
            "severity": "error",
        },
        ErrorCode.FFMPEG: {
            "message": "Media transcoding failed",
            "action": "Ensure ffmpeg is installed and properly configured",
            "severity": "error",
        },
        ErrorCode.THROTTLE: {
            "message": "Platform rate limiting detected",
            "action": "Wait before retrying; exponential backoff is enabled",
            "severity": "info",
        },
        ErrorCode.COOKIE: {
            "message": "Cookie file format invalid or expired",
            "action": "Regenerate cookies and re-submit",
            "severity": "error",
        },
        ErrorCode.UNKNOWN: {
            "message": "An unexpected error occurred",
            "action": "Check logs and try again",
            "severity": "error",
        },
    }

    @classmethod
    def get_advice(cls, error_code: ErrorCode) -> RemediationAdvice:
        """Get remediation advice for an error code."""
        info = cls._ERROR_MESSAGES.get(
            error_code, cls._ERROR_MESSAGES[ErrorCode.UNKNOWN]
        )
        return RemediationAdvice(
            error_code=error_code,
            message=info["message"],
            action=info["action"],
            severity=info["severity"],
        )

    @classmethod
    def message_from_exception(cls, exc: Exception) -> RemediationAdvice:
        """Classify exception and return remediation advice."""
        error_str = str(exc).lower()

        if "network" in error_str or "connection" in error_str:
            code = ErrorCode.NETWORK
        elif "auth" in error_str or "unauthorized" in error_str or "403" in error_str:
            code = ErrorCode.AUTH
        elif "disk" in error_str or "space" in error_str or "28" in error_str:
            code = ErrorCode.DISK
        elif "ffmpeg" in error_str or "transcode" in error_str:
            code = ErrorCode.FFMPEG
        elif "429" in error_str or "too many requests" in error_str:
            code = ErrorCode.THROTTLE
        elif "cookie" in error_str:
            code = ErrorCode.COOKIE
        else:
            code = ErrorCode.UNKNOWN

        return cls.get_advice(code)
