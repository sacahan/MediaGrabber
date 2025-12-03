"""CLI progress rendering for real-time download feedback."""

from __future__ import annotations

import sys
import threading

from ..models.progress_state import ProgressState


class ProgressRenderer:
    """Render progress to console with live updates."""

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose
        self._lock = threading.Lock()
        self._last_percent: float = 0.0

    def render(self, state: ProgressState) -> None:
        """Render a progress state to stdout."""
        with self._lock:
            # Ensure monotonic progress
            if state.percent < self._last_percent:
                state.percent = self._last_percent
            else:
                self._last_percent = state.percent

            # Build output line
            line_parts = [
                f"[{state.status.upper()}]",
                f"{state.percent:.1f}%",
                state.stage,
            ]

            if state.eta_seconds is not None:
                line_parts.append(f"ETA: {state.eta_seconds}s")

            if state.speed is not None:
                speed_mb = state.speed / (1024 * 1024)
                line_parts.append(f"Speed: {speed_mb:.1f} MB/s")

            if state.message:
                line_parts.append(f"({state.message})")

            retry_hints = []
            if state.retry_after_seconds is not None:
                retry_hints.append(f"Retry in {state.retry_after_seconds}s")
            if state.attempts_remaining is not None:
                retry_hints.append(f"{state.attempts_remaining} attempts left")
            if state.remediation:
                retry_hints.append(state.remediation)

            if retry_hints:
                line_parts.append(" | ".join(retry_hints))

            line = " | ".join(line_parts)
            sys.stdout.write(f"\r{line:<100}\n")
            sys.stdout.flush()

    def render_summary(
        self,
        items: list,
        total: int | None = None,
        recommendations: list[str] | None = None,
    ) -> None:
        """Render final summary with item counts and remediation hints."""

        resolved_total = total if total is not None else len(items)
        successful = sum(
            1 for item in items if _get_attr(item, "status") == "completed"
        )
        failed = resolved_total - successful

        sys.stdout.write("\n" + "=" * 80 + "\n")
        sys.stdout.write("Download Complete:\n")
        sys.stdout.write(f"  Total items: {resolved_total}\n")
        sys.stdout.write(f"  Successful: {successful}\n")
        sys.stdout.write(f"  Failed: {failed}\n")

        failed_items = [
            item for item in items if _get_attr(item, "status") != "completed"
        ]
        if failed_items:
            sys.stdout.write("\nFailed items:\n")
            for item in failed_items:
                title = _get_attr(item, "title") or "Unnamed item"
                error_message = _get_attr(item, "error_message") or _get_attr(
                    item, "errorMessage"
                )
                remediation = _get_attr(item, "remediation")
                sys.stdout.write(f"  - {title}: {error_message or 'failed'}\n")
                if remediation:
                    sys.stdout.write(f"    Remediation: {remediation}\n")

        if recommendations:
            sys.stdout.write("\nSuggested actions:\n")
            for rec in recommendations:
                sys.stdout.write(f"  • {rec}\n")

        sys.stdout.write("=" * 80 + "\n")
        sys.stdout.flush()


def _get_attr(item: object, key: str) -> str | None:
    if isinstance(item, dict):
        return item.get(key)  # type: ignore[return-value]
    return getattr(item, key, None)
