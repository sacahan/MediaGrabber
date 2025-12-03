# Research Notes — Unified Download Pipeline Rebuild

## pytubefix download orchestration (YouTube dependency)

- **Decision**: Wrap pytubefix `YouTube` objects inside `download_service.py` with explicit `on_progress` callbacks and throttled playlist iteration to honour per-item delays.
- **Rationale**: pytubefix exposes resilient signature decryption and retry helpers, but only when the client code forwards `use_oauth`/`allow_oauth_cache` flags and respects request throttling; centralising the wrapper keeps CLI/REST parity and gives us one place to insert progress relays.
- **Alternatives considered**: Staying on legacy pytube (breaks frequently and lacks mobile-ready streams); swapping entirely to yt-dlp for YouTube (adds startup latency and loses pytubefix playlist caching benefits).

## yt-dlp for Instagram/Facebook/X (multi-platform dependency)

- **Decision**: Instantiate yt-dlp with per-platform option presets (cookies path, `extract_flat` for playlists off, `http_chunk_size` tuned) and capture hook events to emit `ProgressState` rows.
- **Rationale**: yt-dlp’s option dictionaries let us toggle cookies or throttling per request; reusing a shared preset ensures consistent retries/backoff and simplifies unit testing. Hooking `progress_hooks` is the only supported path to share byte counts with both CLI and REST.
- **Alternatives considered**: Spawning separate subprocesses per download (complicates progress capture) or maintaining bespoke scrapers (too brittle, violates governance focus on mature tooling).

## ffmpeg mobile + fallback profiles (transcode dependency)

- **Decision**: Use a bounded (size 2) asyncio queue that feeds a worker coroutine launching ffmpeg with the primary 720p/1000kbps preset, validating filesize before optionally enqueuing the fallback 480p/700kbps pass.
- **Rationale**: Queue-based fan-in avoids multiple concurrent ffmpeg processes competing for CPU; validating filesize lets us skip unnecessary fallback runs and aligns with the clarified rule (“only fallback when primary exceeds constraints”).
- **Alternatives considered**: Allowing each job to spawn ffmpeg immediately (risks CPU spikes); delegating to systemd-run or OS schedulers (adds deployment complexity and reduces portability).

## Unified progress + observability (integration pattern)

- **Decision**: Define a shared `ProgressState` dataclass plus `ProgressBus` helper that pushes updates both to CLI loggers and an in-memory store for `/api/downloads/{jobId}/progress` polling.
- **Rationale**: Operators require identical fields regardless of surface; a bus abstraction keeps services ignorant of transport details and makes it trivial to inject fake sinks in unit tests while persisting recent states for API consumers.
- **Alternatives considered**: Directly printing/logging inside services (breaks REST parity); persisting progress to disk/database (overkill for short-lived jobs and adds IO contention).
