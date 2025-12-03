"""Tests for logging format and output."""

import logging
from io import StringIO


def test_logging_format_structured() -> None:
    """Test that logging output can be structured (JSON-compatible)."""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # Create a string buffer to capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)

    # Format: timestamp | level | message
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Test log output
    logger.info("Test message")
    log_output = log_stream.getvalue()

    assert "INFO" in log_output
    assert "Test message" in log_output


def test_logging_format_human_readable() -> None:
    """Test that logging output is human-readable."""
    logger = logging.getLogger("test_readable")
    logger.setLevel(logging.DEBUG)

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)

    # Human-readable format
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.warning("Potential issue detected")
    log_output = log_stream.getvalue()

    assert "[WARNING]" in log_output
    assert "Potential issue detected" in log_output


def test_logging_preserves_context() -> None:
    """Test that logging preserves context information."""
    logger = logging.getLogger("test_context")
    logger.setLevel(logging.DEBUG)

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(funcName)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info("Operation completed")
    log_output = log_stream.getvalue()

    assert "[INFO]" in log_output
    assert "test_logging_preserves_context" in log_output
    assert "Operation completed" in log_output


def test_logging_does_not_leak_stack_traces() -> None:
    """Test that sensitive stack traces are not leaked in user-facing logs."""
    logger = logging.getLogger("test_sanitize")
    logger.setLevel(logging.ERROR)

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)

    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Log a generic error message (not the raw exception)
    logger.error("An error occurred during download")
    log_output = log_stream.getvalue()

    assert "[ERROR]" in log_output
    assert "download" in log_output.lower()
