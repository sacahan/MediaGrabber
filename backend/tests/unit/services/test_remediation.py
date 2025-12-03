"""Tests for remediation service."""

from backend.app.services.remediation import (
    ErrorCode,
    RemediationService,
)


def test_remediation_network_error() -> None:
    """Test remediation for network errors."""
    advice = RemediationService.get_advice(ErrorCode.NETWORK)
    assert advice.error_code == ErrorCode.NETWORK
    assert "Network" in advice.message
    assert "internet" in advice.action.lower()
    assert advice.severity == "warning"


def test_remediation_auth_error() -> None:
    """Test remediation for authentication errors."""
    advice = RemediationService.get_advice(ErrorCode.AUTH)
    assert advice.error_code == ErrorCode.AUTH
    assert "Authentication" in advice.message
    assert "cookies" in advice.action.lower()
    assert advice.severity == "error"


def test_remediation_disk_error() -> None:
    """Test remediation for disk space errors."""
    advice = RemediationService.get_advice(ErrorCode.DISK)
    assert advice.error_code == ErrorCode.DISK
    assert "Insufficient disk space" in advice.message
    assert "Free" in advice.action
    assert advice.severity == "error"


def test_remediation_ffmpeg_error() -> None:
    """Test remediation for ffmpeg errors."""
    advice = RemediationService.get_advice(ErrorCode.FFMPEG)
    assert advice.error_code == ErrorCode.FFMPEG
    assert "transcoding" in advice.message.lower()
    assert advice.severity == "error"


def test_remediation_throttle_error() -> None:
    """Test remediation for rate limit errors."""
    advice = RemediationService.get_advice(ErrorCode.THROTTLE)
    assert advice.error_code == ErrorCode.THROTTLE
    assert "rate limiting" in advice.message.lower()
    assert "backoff" in advice.action.lower()
    assert advice.severity == "info"


def test_remediation_unknown_error() -> None:
    """Test remediation for unknown errors."""
    advice = RemediationService.get_advice(ErrorCode.UNKNOWN)
    assert advice.error_code == ErrorCode.UNKNOWN
    assert "unexpected" in advice.message.lower()
    assert advice.severity == "error"


def test_classify_network_exception() -> None:
    """Test exception classification for network errors."""
    exc = RuntimeError("Connection refused")
    advice = RemediationService.message_from_exception(exc)
    assert advice.error_code == ErrorCode.NETWORK


def test_classify_auth_exception() -> None:
    """Test exception classification for auth errors."""
    exc = RuntimeError("Unauthorized 403")
    advice = RemediationService.message_from_exception(exc)
    assert advice.error_code == ErrorCode.AUTH


def test_classify_disk_exception() -> None:
    """Test exception classification for disk errors."""
    exc = RuntimeError("No space left on device (28)")
    advice = RemediationService.message_from_exception(exc)
    assert advice.error_code == ErrorCode.DISK


def test_classify_throttle_exception() -> None:
    """Test exception classification for throttle errors."""
    exc = RuntimeError("HTTP 429 Too Many Requests")
    advice = RemediationService.message_from_exception(exc)
    assert advice.error_code == ErrorCode.THROTTLE


def test_classify_ffmpeg_exception() -> None:
    """Test exception classification for ffmpeg errors."""
    exc = RuntimeError("ffmpeg transcode failed")
    advice = RemediationService.message_from_exception(exc)
    assert advice.error_code == ErrorCode.FFMPEG
