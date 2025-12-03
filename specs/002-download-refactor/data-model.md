# Data Model — Unified Download Pipeline Rebuild

## Entity Overview

| Entity           | Purpose                                                                            | Key Relationships                                                                                |
| ---------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| DownloadJob      | Canonical record for each download/transcode request, regardless of entry surface. | Owns many `ProgressState` events and `DownloadArtifact` rows; references one `TranscodeProfile`. |
| ProgressState    | Snapshot of job telemetry exposed to CLI logs and `/progress` API.                 | Belongs to one `DownloadJob`.                                                                    |
| TranscodeProfile | Configuration bundle for primary + fallback ffmpeg presets.                        | Linked by reference from `DownloadJob`.                                                          |
| DownloadArtifact | Describes generated files (video/audio/archive) to expose to clients.              | Belongs to `DownloadJob`; playlist jobs may generate multiple artifacts.                         |
| PlaylistPackage  | Virtual aggregate describing ZIP packaging and per-item results for playlists.     | References multiple `DownloadArtifact` items and shares the parent `DownloadJob`.                |

## DownloadJob

- **Fields**
  - `jobId: str` — ULID/UUID generated at submission time.
  - `sourceUrl: str` — Original media or playlist URL.
  - `platform: Literal["youtube","instagram","facebook","x"]` — Derived via URL parser.
  - `requestedFormat: Literal["mp4","mp3","zip"]` — CLI/API input, determines target artifact.
  - `downloadBackend: Literal["pytubefix","yt-dlp"]` — Auto-selected, stored for telemetry.
  - `profile: TranscodeProfileRef` — Dict containing selected primary/fallback presets.
  - `status: Literal["pending","downloading","transcoding","completed","failed","queued"]` — High-level state for CLI/API.
  - `stage: Literal["init","download","transcoding","packaging","cleanup"]` — Granular pipeline pointer for progress UI.
  - `outputDir: str` — Absolute path under `output/{jobId}`.
  - `requestedAt: datetime` / `updatedAt: datetime` — Tracking for SLAs.
  - `error: Optional[DownloadError]` — Populated on failure with remediation text.
  - `playlistItems: Optional[List[PlaylistItemResult]]` — Present when batching playlist steps.
- **Validation Rules**
  - `sourceUrl` MUST pass platform-specific regex/hostname allowlist.
  - `requestedFormat` MUST be compatible with platform (e.g., MP3 only for YouTube audio streams).
  - `platform` + `downloadBackend` MUST map to supported combinations (YouTube→pytubefix, others→yt-dlp).
  - `status` transitions allowed only via state machine below.
- **State Transitions**
  - `pending → queued` when entering the ffmpeg queue for transcode.
  - `pending → downloading → (transcoding|packaging) → completed` for successful runs.
  - Any state → `failed` when unrecoverable error occurs (retain last stage for diagnostics).
  - `queued → downloading` only when queue worker hands back control for fallback attempt.

## ProgressState

- **Fields**
  - `jobId: str`
  - `status: Literal["queued","downloading","transcoding","packaging","completed","failed"]`
  - `stage: str` — Human-readable phrase (e.g., "Downloading 3/12").
  - `percent: float` — 0–100 monotonic progress.
  - `downloadedBytes: int`
  - `totalBytes: Optional[int]`
  - `speed: Optional[float]` — Bytes per second.
  - `etaSeconds: Optional[int]`
  - `message: str` — Remediation or contextual text.
  - `timestamp: datetime`
- **Validation Rules**
  - `percent` MUST be clamped to `[0,100]` and non-decreasing per job.
  - `status` and `stage` must remain in sync with `DownloadJob.status` transitions.
  - `message` MUST be English plain text with actionable hints when errors occur.

## TranscodeProfile

- **Fields**
  - `name: Literal["mobile-primary","mobile-fallback"]`
  - `resolution: Tuple[int,int]`
  - `videoBitrateKbps: int`
  - `audioBitrateKbps: int`
  - `maxFilesizeMb: int`
  - `crf: int`
  - `container: Literal["mp4","mp3"]`
- **Validation Rules**
  - `mobile-primary` fixed at 720p/1000kbps; `mobile-fallback` fixed at 480p/700kbps per spec.
  - `maxFilesizeMb` MUST be <= platform requirements (default 50 MB for IG/FB, configurable).

## DownloadArtifact

- **Fields**
  - `jobId: str`
  - `artifactId: str`
  - `type: Literal["video","audio","archive"]`
  - `path: str` — Relative path under `output/{jobId}`.
  - `sizeBytes: int`
  - `expiresAt: Optional[datetime]`
  - `checksum: Optional[str]`
- **Validation Rules**
  - `path` MUST resolve inside the job’s output directory.
  - `artifactId` unique per job for front-end download listing.
  - `expiresAt` optional; when set it must be in the future.

## PlaylistPackage

- **Fields**
  - `jobId: str`
  - `zipPath: Optional[str]`
  - `successItems: List[PlaylistItemResult]`
  - `failedItems: List[PlaylistItemResult]`
- **Validation Rules**
  - Package only materialises when >1 artifacts exist.
  - `failedItems` MUST include remediation text returned from underlying service.

## Relationships & Derived Views

- `DownloadJob` 1—N `ProgressState`: progress bus stores timeline for API polling.
- `DownloadJob` 1—N `DownloadArtifact`: CLI/API responses include artifact list per job.
- `DownloadJob` 1—1 `TranscodeProfile` (current active profile pair) but retains historical runs through event log.
- `PlaylistPackage` aggregates `DownloadArtifact` instances but references the same `jobId` for cleanup.

## Derived/Computed Data

- `compressionRatio = 1 - (finalSize / originalSize)` stored alongside artifacts to satisfy SC-004 reporting.
- `retryCount` derived from exponential backoff tracker for FR-007 telemetry.
- `queueWaitSeconds` computed from timestamp delta between entering/leaving ffmpeg queue, surfaced in operator dashboards.
