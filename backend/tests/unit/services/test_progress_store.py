"""Tests for progress store service."""

from backend.app.models.progress_state import ProgressState
from backend.app.services.progress_store import ProgressStore


def test_progress_store_records_state() -> None:
    """Test that progress store records states."""
    store = ProgressStore(ttl_seconds=3600)
    state = ProgressState(
        job_id="job1",
        status="downloading",
        stage="Initializing",
        percent=0.0,
        message="Starting download",
    )

    store.record(state)
    latest = store.get_latest("job1")

    assert latest is not None
    assert latest.job_id == "job1"
    assert latest.status == "downloading"


def test_progress_store_gets_latest() -> None:
    """Test that store returns latest state."""
    store = ProgressStore(ttl_seconds=3600)

    state1 = ProgressState(
        job_id="job1",
        status="downloading",
        stage="Stage 1",
        percent=25.0,
        message="Message 1",
    )
    state2 = ProgressState(
        job_id="job1",
        status="transcoding",
        stage="Stage 2",
        percent=50.0,
        message="Message 2",
    )

    store.record(state1)
    store.record(state2)

    latest = store.get_latest("job1")
    assert latest is not None
    assert latest.status == "transcoding"
    assert latest.percent == 50.0


def test_progress_store_get_history() -> None:
    """Test that store returns full history."""
    store = ProgressStore(ttl_seconds=3600)

    for i in range(5):
        state = ProgressState(
            job_id="job1",
            status="downloading",
            stage=f"Stage {i}",
            percent=float(i * 20),
            message=f"Progress {i}",
        )
        store.record(state)

    history = store.get_history("job1")
    assert len(history) == 5
    assert history[0].percent == 0.0
    assert history[4].percent == 80.0


def test_progress_store_returns_empty_for_unknown_job() -> None:
    """Test that store returns empty for unknown job."""
    store = ProgressStore(ttl_seconds=3600)

    latest = store.get_latest("unknown")
    assert latest is None

    history = store.get_history("unknown")
    assert history == []


def test_progress_store_ttl_cleanup() -> None:
    """Test that expired records are cleaned up."""
    store = ProgressStore(ttl_seconds=1)

    # Record initial state
    state = ProgressState(
        job_id="job1",
        status="downloading",
        stage="Initial",
        percent=0.0,
        message="Starting",
    )
    store.record(state)

    # Verify record exists
    latest = store.get_latest("job1")
    assert latest is not None

    # Wait for TTL to expire and cleanup
    import time

    time.sleep(2)

    expired = store.cleanup_expired()
    assert expired > 0

    # Verify record is gone
    latest = store.get_latest("job1")
    assert latest is None


def test_progress_store_queue_depth() -> None:
    """Test that queue depth counts queued/transcoding jobs."""
    store = ProgressStore(ttl_seconds=3600)

    # Add completed job
    state1 = ProgressState(
        job_id="job1",
        status="completed",
        stage="Done",
        percent=100.0,
        message="Completed",
    )
    store.record(state1)

    # Add queued job
    state2 = ProgressState(
        job_id="job2",
        status="queued",
        stage="Waiting",
        percent=10.0,
        message="In queue",
    )
    store.record(state2)

    # Add transcoding job
    state3 = ProgressState(
        job_id="job3",
        status="transcoding",
        stage="Transcoding",
        percent=50.0,
        message="Encoding",
    )
    store.record(state3)

    depth = store.get_queue_depth()
    assert depth == 2  # Only queued and transcoding count


def test_progress_store_history_limit() -> None:
    """Test that history respects limit parameter."""
    store = ProgressStore(ttl_seconds=3600)

    # Add many states
    for i in range(50):
        state = ProgressState(
            job_id="job1",
            status="downloading",
            stage=f"Stage {i}",
            percent=float(i),
            message=f"Message {i}",
        )
        store.record(state)

    # Get history with limit
    history = store.get_history("job1", limit=10)
    assert len(history) == 10
    assert history[0].percent == 40.0  # Last 10 items
    assert history[9].percent == 49.0
