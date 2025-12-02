# Feature Specification: Unified Download Pipeline Refactor

**Feature Branch**: `[001-download-pipeline-refactor]`
**Created**: 2025-12-02
**Status**: Draft
**Input**: User description: "對現有下載流程進行重構：YouTube 使用 pytubefix、其他平台使用 yt-dlp，並為所有下載內容提供行動裝置友善的轉碼。"

## User Scenarios & Testing (mandatory)

### User Story 1 - CLI retains parity for YouTube downloads (Priority: P1)

資深使用 CLI 的自動化工程師想要下載單支或播放清單的 YouTube 內容，
並立即獲得已轉碼為行動裝置友善格式的 MP4/MP3。

**Why this priority**: CLI 是現有自動化流程的關鍵入口，需先確保重構後仍可無縫運作。

**Independent Test**: 從 CLI 執行 `python media_grabber.py <youtube_url>`，確認輸出檔
案能在手機播放並且 CLI 日誌顯示新轉碼階段。

**Acceptance Scenarios**:

1. **Given** 使用者提供單支 YouTube URL 與 `--format mp4`, **When** 執行 CLI 指令,
   **Then** 下載與轉碼皆成功且輸出檔案符合 720p 以下的行動裝置設定。
2. **Given** 使用者提供 YouTube 播放清單並選擇 MP3, **When** CLI 逐一下載, **Then** 每
   首歌都轉成 MP3 並產生播放清單 ZIP, 日誌包含逐項轉碼進度。

---

### User Story 2 - Web UI delivers mobile-ready downloads for other platforms (Priority: P1)

一般使用者透過 Web 介面下載 Instagram、Facebook、X/Twitter 影片時，希望直接
獲得適合手機分享的 MP4 檔案，並在前端看到轉碼進度。

**Why this priority**: Web UI 是主要的互動介面，需確保非 YouTube 平台的下載品質與體驗。

**Independent Test**: 透過 Web 介面輸入 Instagram 影片 URL，點擊下載後取得壓縮
轉碼的 MP4，並從進度面板看到 "transcoding" 階段。

**Acceptance Scenarios**:

1. **Given** 使用者輸入 Instagram Reel URL, **When** 點選下載, **Then** 後端使用
   yt-dlp 抓取影片並完成行動化轉碼, 前端顯示完成訊息與檔案大小。
2. **Given** 使用者下載 Facebook 影片, **When** 伺服器偵測原始檔案超過 50MB,
   **Then** 仍能透過轉碼降低大小並提供下載, 若超出限制則給出清楚的錯誤與建議。

---

### User Story 3 - Operators monitor unified pipeline health (Priority: P2)

維運人員需要一套統一的進度與錯誤回報格式，以便透過日誌或儀表板追蹤 CLI 與
Web 下載、轉碼流程。

**Why this priority**: 保持 CLI 與 Web 的 observability 等效，有助於偵錯與 SLA 追蹤。

**Independent Test**: 觸發任一平台下載並查看後端日誌或 API 回應，確認包含
download 與 transcoding 階段資訊，且結構一致。

**Acceptance Scenarios**:

1. **Given** 任一下載任務啟動, **When** 查詢 `/progress/<job_id>` 或 CLI 日誌,
   **Then** 進度回傳包含 `stage="transcoding"` 與 eta, speed 等欄位。
2. **Given** 轉碼失敗或 ffmpeg 不可用, **When** 管理者檢視日誌, **Then** 可看到根本
   原因與建議行動（例如重新安裝 ffmpeg），同時任務標記為失敗。

---

### Edge Cases

- 下載來源平台因登入或 geo 封鎖導致 yt-dlp 無法取得資料時如何回報？
- 轉碼過程中磁碟空間不足時系統如何中止並釋放暫存檔案？
- 使用者同時觸發多項下載是否會造成 ffmpeg 資源競爭？
- 如何處理播放清單中部分影片無法下載或需登入的狀況？
- 手機最佳化轉碼後若檔案仍超過社群平台限制時的 fallback 流程？

## Requirements (mandatory)

### Functional Requirements

- **FR-001**: System MUST 使用 pytubefix 處理所有 YouTube 單影片與播放清單下載，
  支援 MP4 與 MP3 兩種輸出。
- **FR-002**: System MUST 使用 yt-dlp 處理 Facebook、Instagram、X/Twitter 等非
  YouTube 平台的下載需求。
- **FR-003**: CLI 與 Web API MUST 共用核心服務層，並提供一致的輸入參數與輸出
  欄位（含轉碼設定）。
- **FR-004**: 所有成功下載的媒體 MUST 經由 ffmpeg 轉碼，符合預設手機分享規格（
  720p、1000kbps、128kbps audio 可調）。
- **FR-005**: 下載與轉碼過程 MUST 回報 `download`、`transcoding`、`completed` 等
  階段與百分比，供 CLI 與 Web 顯示。
- **FR-006**: 當轉碼失敗或 ffmpeg 不可用時，需提供清楚錯誤訊息與
  fallback（保留原檔或通知使用者）。
- **FR-007**: Playlist 下載時 MUST 支援逐項轉碼並生成 ZIP 檔，同步提供失敗清單。
- **FR-008**: System MUST 記錄每次真實整合測試的結果到 `backend/TEST_RESULTS.md`，
  包含測試 URL 與轉碼成品資訊。
- **FR-009**: System MUST 支援可配置的轉碼參數（如解析度、比特率）以便未來擴充。

### Key Entities (include if feature involves data)

- **DownloadJob**: 描述單次下載任務的平台、來源 URL、目標格式、轉碼設定、進度狀態
  與輸出位置。
- **TranscodeProfile**: 儲存不同行動裝置需求的轉碼參數（解析度、比特率、音訊設定）。
- **ProgressState**: 追蹤 download、transcoding、completed、failed 等階段的百分比與
  錯誤訊息。

## Success Criteria (mandatory)

### Measurable Outcomes

- **SC-001**: CLI 執行單支 YouTube 影片下載＋轉碼流程的成功率達 95% 以上（以 20 次
  真實測試計算）。
- **SC-002**: Web UI 下載 Instagram/Twitter 影片的平均完成時間（含轉碼）控制在
  120 秒以內（檔案 < 3 分鐘）。
- **SC-003**: 100% 的下載任務在進度 API 或 CLI 日誌中正確顯示 `transcoding` 階段與完成
  百分比。
- **SC-004**: 轉碼後的 MP4 檔案相較原始檔案平均縮小至少 30%，並可在最新 iOS/Android
  裝置上順利播放。
