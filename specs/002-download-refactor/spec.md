# Feature Specification: Unified Download Pipeline Rebuild

**Feature Branch**: `[002-download-refactor]`
**Created**: 2025-12-02
**Status**: Draft
**Input**: User description: "對現有下載流程進行重構：YouTube 使用 pytubefix、其他平台使用 yt-dlp，並為所有下載內容提供行動裝置友善的轉碼。"

## Clarifications

### Session 2025-12-02

- Q: 什麼情況下需要啟動 fallback 行動轉碼？ → A: 僅當主轉碼完成但產物仍超出平台大小或位元率限制時才啟動 fallback。
- Q: `/api/downloads` 需採取何種驗證與節流策略？ → A: API 為公開端點，不實作內建驗證或節流，限制交由部署層處理。
- Q: 轉碼服務預設要如何限制 ffmpeg 併發？ → A: 以全域 FIFO 佇列限制同時最多 2 個 ffmpeg 工作，其他排隊待處理。

## User Scenarios & Testing (mandatory)

### User Story 1 - CLI delivers mobile-ready YouTube downloads (Priority: P1)

資深自動化工程師透過全新的 CLI 入口 (`backend/app/cli/main.py`) 下載 YouTube 單影片或播放清單，期待立即取得行動裝置最佳化的 MP4/MP3 成品並保留可追蹤的任務 ID。

**Why this priority**: CLI 是既有自動化流程的核心，必須率先確保重建後仍可穩定提供行動裝置友善的影音輸出。

**Independent Test**: 於 CLI 執行 `python -m app.cli.main download --url <youtube_url> --format mp4`，驗證輸出檔案可於手機播放且進度日誌含 download/transcoding 階段。

**Acceptance Scenarios**:

1. **Given** 使用者提供 YouTube 單影片 URL 與 `--format mp4`, **When** 執行 CLI 指令, **Then** 任務成功並產出 720p/1000kbps 的 MP4，進度輸出含百分比與 ETA。
2. **Given** 使用者提供 YouTube 播放清單與 `--format mp3`, **When** CLI 逐項下載, **Then** 每首歌曲轉成 MP3 並於任務目錄內生成 ZIP，任務摘要列出成功與失敗項目。

> **Parity note**: CLI 與 REST 共用 `download_service.py` 與 `transcode_service.py`，因此 Web 介面同樣支援 YouTube 單片與播放清單（MP4/MP3）；此故事僅突出 CLI 情境。

---

### User Story 2 - Web UI handles non-YouTube platforms (Priority: P1)

一般使用者透過全新 REST API (`/api/downloads`) 下載 Instagram、Facebook、X 影片，期望立即獲得行動裝置合規的 MP4，並在前端控制台看到完整進度與錯誤提示。

**Why this priority**: Web 是主要流量來源，必須確保非 YouTube 平台也能受惠於統一管線與轉碼策略。

**Independent Test**: 透過瀏覽器提交 Instagram Reel URL，於前端觀察 `transcoding` 階段並下載完成的 MP4，檔案大小低於預設 50MB。

**Acceptance Scenarios**:

1. **Given** 使用者輸入 Instagram Reel URL, **When** 提交下載請求, **Then** 後端以 yt-dlp 抓取並完成主轉碼，前端顯示完成訊息與檔案大小。
2. **Given** Facebook 影片原檔超過 50MB, **When** 觸發下載, **Then** 系統自動執行 fallback 轉碼 (480p/700kbps) 並於成功時提示壓縮比例；若仍超標則傳回含 remediation 的錯誤。

> **Parity note**: REST API 與 CLI 具備相同的多平台支援（YouTube、Instagram、Facebook、X），此故事僅強調 Web 流量主導的非 YouTube 情境。

---

### User Story 3 - Operators monitor unified pipeline health (Priority: P2)

維運人員透過 CLI 日誌與 `/api/downloads/{jobId}/progress` API 監控任務狀態，期待看到一致的欄位（`status`, `stage`, `percent`, `eta`）與錯誤修復建議，以便快速定位問題。

**Why this priority**: 可觀測性是降低停機風險與支援多入口併發的基礎。

**Independent Test**: 觸發跨平台任務並查詢進度 API，確認回傳結構與 CLI 日誌同步，且錯誤案例包含 remediation 建議。

**Acceptance Scenarios**:

1. **Given** 任務進入轉碼階段, **When** 查詢進度 API, **Then** 回傳含 `stage="transcoding"`、`percent`、`downloadedBytes`、`etaSeconds` 的 JSON。
2. **Given** ffmpeg 缺失或轉碼出錯, **When** 監控人員檢視任務, **Then** 任務標記為 failed 並提供「安裝 ffmpeg」或「稍後重試」等具體 remediation。

---

### Edge Cases

- 平台因登入或區域限制拒絕下載時，任務需回傳明確錯誤與建議（提供 cookies、調整 proxy）。
- 轉碼期間磁碟或暫存空間不足時，系統如何中止、清理暫存並回報狀態。
- 同時觸發多個轉碼任務時，如何序列化或限制並行以避免 ffmpeg 競爭資源。
- 播放清單中部分影片無法取得時，成功與失敗項目如何彙整並呈現給使用者；整個播放清單任務應標示為 `completed` 若至少一項成功，`failed` 若全數失敗，ZIP 內 `SUMMARY.json` 應清楚記錄各項目狀態（`itemId`、`sourceUrl`、`status`、`artifactPath`、`sizeBytes`、`error.code`、`error.remediation`）。
- 進度回報可能因網路抖動重複或倒退時，如何確保 percent 單調遞增並記錄異常。
- 播放清單任務若部分項目在 ffmpeg 佇列中等待，CLI 需展示隊列深度（如「3 of 5 transcoding, 2 queued」），REST API 的進度事件應包含 `queueDepth` 與 `queuePosition` 欄位。

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: 系統 MUST 在全新下載服務模組 (`backend/app/services/download_service.py`) 中路由平台，針對 YouTube 使用 pytubefix，針對 Facebook/Instagram/X 使用 yt-dlp。
- **FR-002**: 系統 MUST 建立新的轉碼服務模組 (`backend/app/services/transcode_service.py`)，執行 mobile primary profile (720p/1000kbps)，僅當主轉碼完成但仍超出平台大小/位元率限制時，才自動啟動 fallback profile (480p/700kbps)。
- **FR-003**: CLI MUST 透過新入口 (`python -m app.cli.main`) 呼叫統一服務層，提供下載、播放清單、重試、查詢任務狀態等指令。CLI 播放清單指令 MUST 支援 `--url <playlist_url>` 必填、`--format mp3/mp4` 預設 mp4、`--zip` 預設啟用、`--cookies-file <path>` 可選提供驗證。
- **FR-004**: REST API MUST 於新 blueprint (`backend/app/api/downloads.py`) 暴露 `/api/downloads`、`/api/downloads/{jobId}`、`/api/downloads/{jobId}/progress`，並與 CLI 使用同一服務層與資料模型。REST POST body 播放清單提交 MUST 包含 `url` 必填、`format` 預設 mp4、`playlistZip` 預設 true、`cookiesBase64` 可選，回傳欄位與 CLI 對等。
- **FR-005**: 所有下載任務 MUST 產生標準化進度事件，包含 `status`, `stage`, `percent`, `downloadedBytes`, `totalBytes`, `speed`, `etaSeconds`, `message`，且 CLI 與 API 回傳欄位一致。
- **FR-006**: 系統 MUST 支援 playlist 打包流程，在所有項目完成後自動產生 ZIP，並於回應中標示成功與失敗列表。ZIP 檔案結構 MUST 包含：個別媒體檔案、`SUMMARY.json`（含 per-item 狀態與 remediation）、`COMPRESSION_REPORT.txt`（彙整壓縮比例），內容順序 MUST 依原 URL 清單順序組織。
- **FR-007**: 若平台回應節流或錯誤，系統 MUST 以指數退避（預設 3 次、起始延遲 3 秒）重試，仍失敗則回傳明確錯誤與建議。
- **FR-008**: 系統 MUST 於 `output/{jobId}/` 建立隔離的工作目錄，流程結束後依任務狀態進行清理並保留可下載檔案。
- **FR-009**: 系統 MUST 記錄每次真實整合測試結果至 `backend/TEST_RESULTS.md`，包含來源 URL、下載耗時、轉碼產物大小與成功狀態。
- **FR-010**: 系統 MUST 提供可配置的轉碼與併發上限（例如透過設定檔或環境變數），並保證函式長度 ≤ 50 行。
- **FR-011**: REST API MUST 允許匿名請求且不實作內建節流/驗證，並於文件標示由部署層（例如 WAF 或 edge）負責任何流量管理，後端僅回傳 200/4xx 錯誤。
- **FR-012**: 轉碼服務 MUST 以全域 FIFO 佇列控制 ffmpeg 併發，預設僅允許 2 個同時進行的轉碼工作（可設定），額外任務排隊並透過進度事件回報等待狀態。排隊中的任務 MUST 於進度事件中設定 `status="queued"`、`stage="Waiting for ffmpeg (position X/Y)"` 並保持 `percent` 不變。
- **FR-013**: REST `/api/downloads/{jobId}` 回傳的播放清單資料 MUST 包含 `playlistItems` 陣列，每個項目含 `itemId`、`sourceUrl`、`status`、`artifact` 及 `error`（失敗時含 `code`、`message`、`remediation`）。CLI 任務摘要 MUST 列出逐項的序號、來源 URL、狀態（成功/失敗）、檔名/大小、及失敗時的 remediation（如「需提供 cookies」）。
- **FR-014**: CLI 與 REST 中若播放清單包含混合媒體類型（音訊/影片），系統 MUST 遵循 `--format` 參數統一轉換流程，如 `--format mp3` 則全數轉成 MP3（包括原本為影片的項目），`--format mp4` 則全數轉成 MP4。
- **FR-015**: 播放清單下載若部分項目因登入限制或地域限制拒絕，系統 MUST 允許使用者提供平台 cookies 以重試：CLI 支援 `--cookies-file <path>` 指定檔案路徑，REST 接受 `cookiesBase64` 欄位；系統 MUST 自動重試失敗項目並記錄 remediation（如「已提供 cookies，重試中」）。

### Key Entities (include if feature involves data)

- **DownloadJob**: 描述單次任務的 jobId、sourceUrl、platform、requestedFormat、downloadBackend、profile 設定、outputDir、status、timestamps。
- **TranscodeProfile**: 封裝主/備兩組轉碼參數（解析度、bitrate、音訊配置、maxFilesizeMb、crf）。
- **ProgressState**: 進度事件資料結構，包含 jobId、status、stage、percent、downloadedBytes、totalBytes、speed、etaSeconds、message、timestamp。
- **DownloadArtifact**: 記錄產生的檔案類型（video/audio/archive）、路徑、大小、有效期限，用於前端或 CLI 提供下載連結。

## Success Criteria (mandatory)

### Measurable Outcomes

- **SC-001**: 使用新的 CLI 指令下載並轉碼 20 個 YouTube 任務時，成功率 ≥ 95%，且每次產出可於最新 iOS/Android 裝置播放。
- **SC-002**: Web UI 下載 Instagram/Facebook 影片（長度 ≤ 3 分鐘）至任務完成的平均時間 ≤ 120 秒，含主轉碼或 fallback。
- **SC-003**: 100% 任務在 CLI 與進度 API 中皆能呈現 `download`、`transcoding`、`completed/failed` 階段，且 `percent` 單調遞增無倒退紀錄。
- **SC-004**: 行動轉碼產物平均比原始檔案小至少 30%，並提供自動化報告記錄壓縮比例。
