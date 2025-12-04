# Quickstart — Unified Download Pipeline Rebuild

## Prerequisites

1. Python 3.12 with ffmpeg (4.x+) on PATH.
2. Node.js 20+ for Svelte dev server.
3. Network egress to YouTube, Instagram, Facebook, and X.
4. Optional: platform cookies stored under `backend/cookies/{platform}.txt` for geo-restricted URLs.

> **CLI/REST parity**：無論是 CLI (`python -m app.cli.main ...`) 還是 REST (`/api/downloads*`)，都會呼叫相同的下載／轉碼服務，因此底層的 MG\_\* 環境變數與 platform/format 矩陣必須一致。

## Environment setup

```bash
cp .env.example .env
```

Update the values as needed (both CLI 與 REST 都會使用這些設定):

- `MG_MAX_TRANSCODE_WORKERS=2` 限制 ffmpeg 併發數。
- `MG_OUTPUT_DIR=output` 指定統一的輸出根目錄。
- `MG_PROGRESS_TTL_SECONDS=300` 控制 `/progress` 緩存保留時間。

重新啟動 Flask 服務並在新的 CLI session 中載入 `.env` 後再進行後續步驟。

## Backend setup

```bash
cd /Users/sacahan/Documents/workspace/MediaGrabber
pip install -e .
python -m pip install pytubefix yt-dlp
ruff check backend/
```

Start the Flask service (used by REST + frontend):

```bash
cd backend && python -m app.web
```

Environment knobs:

- `MG_MAX_TRANSCODE_WORKERS=2` (default) caps ffmpeg concurrency.
- `MG_OUTPUT_DIR=output` overrides artifact root.
- `MG_PROGRESS_TTL_SECONDS=300` keeps progress history for polling.

## CLI workflow

```bash
python -m app.cli.main download --url https://youtu.be/abc123 --format mp4
python -m app.cli.main playlist --url https://youtube.com/playlist?... --format mp3
python -m app.cli.main status --job-id <JOB_ID>
python -m app.cli.main retry --job-id <JOB_ID>
```

Expected behaviour:

- CLI logs progress lines exposing `status`, `stage`, `percent`, `eta`.
- Playlist runs emit ZIP artifacts under `output/{jobId}/` along with per-item summaries.

## REST workflow

Submit a job:

```bash
curl -X POST https://localhost:8080/api/downloads \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.instagram.com/reel/...","format":"mp4"}'
```

Poll job status and progress:

```bash
curl https://localhost:8080/api/downloads/<JOB_ID>
curl https://localhost:8080/api/downloads/<JOB_ID>/progress
```

Expect `202` on submission, `200` thereafter with artifacts list plus compression metrics.

### REST Progress Response (T045: FR-007, FR-012)

The `/progress` endpoint returns detailed progress with retry and remediation hints:

```json
{
  "jobId": "uuid",
  "status": "downloading|transcoding|completed|failed",
  "stage": "downloading",
  "percent": 45.5,
  "downloadedBytes": 12345678,
  "totalBytes": 27000000,
  "speed": 1048576,
  "etaSeconds": 15,
  "message": "Fetching metadata...",
  "queueDepth": 2,
  "queuePosition": 1,
  "retryAfterSeconds": null,
  "attemptsRemaining": 3,
  "remediation": {
    "code": "TRANSCODE_FAILED_OVERSIZED",
    "message": "Mobile profile exceeded 50MB; trying fallback codec.",
    "suggestedAction": "Check ffmpeg version or try a lower resolution.",
    "category": "retry"
  }
}
```

### Instagram/Facebook/X with Cookies (T025, FR-015)

For platform-restricted content, extract cookies and send as base64:

**From browser DevTools:**

1. Open Instagram/Facebook in private window
2. DevTools → Storage → Cookies
3. Export as JSON, encode as base64

**REST submission with cookies:**

```bash
COOKIES_JSON=$(cat instagram_cookies.json)
COOKIES_B64=$(echo -n "$COOKIES_JSON" | base64)

curl -X POST https://localhost:8080/api/downloads \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://www.instagram.com/reel/...\",\"format\":\"mp4\",\"cookiesBase64\":\"$COOKIES_B64\"}"
```

**Web UI:**
Paste the cookies JSON directly into the "Cookies" field and submit. The UI will encode and transmit automatically.

## Frontend workflow

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, paste a URL, and watch the console reflect the same progress payload as CLI/logging.

## Testing cadence

1. `pytest backend/tests/unit -q` for service coverage.
2. `pytest backend/tests/contract -q` to verify CLI vs REST parity.
3. `pytest backend/tests/integration -k real_urls` after configuring real URLs via env vars.
4. After each integration run, append results to `backend/TEST_RESULTS.md` (URL, duration, artifact size, success/fail, remediation).

## Observability + ops checks

- Inspect `backend/logs/*.log` for structured JSON plus human-readable messages.
- `/api/downloads/{jobId}/progress` retains the latest event per job (5 minutes) for dashboards.
- Queue depth and ffmpeg worker status are exported via CLI `python -m app.cli.main queue` (planned) or logs.
