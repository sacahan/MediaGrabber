# 任務：統一下載管線重建

**輸入**：`/specs/002-download-refactor/` 中的設計文件
**前置需求**：plan.md、spec.md、research.md、data-model.md、contracts/

**測試策略**：每個使用者故事都需涵蓋契約 + 整合測試，因規格要求 CLI/REST 同質性與真實世界驗證（MG-G1、MG-G2）。

**任務編組**：依使用者故事（US1–US3）分層，並先完成設定／基礎階段。

## 第 1 階段：設定（共用基礎建設）

- [x] T001 更新 `pyproject.toml` 後端相依，鎖定 `pytubefix` 與 `yt-dlp` 版本並加入 ffmpeg 輔助選用套件。
- [x] T002 在根目錄新增 `.env.example`，說明 `MG_MAX_TRANSCODE_WORKERS`、`MG_OUTPUT_DIR`、`MG_PROGRESS_TTL_SECONDS` 等 quickstart 會引用的預設值。
- [x] T003 [P] 擴寫 `README.md` 與 `quickstart.md`，加入 CLI/REST 同質性說明與兩種入口的環境設定步驟。

---

## 第 2 階段：基礎建設（阻擋性前置作業）

**目的**：建立所有使用者故事共用的核心模組／服務／設定。

- [x] T004 依 data-model.md 在 `backend/app/models/download_job.py`、`progress_state.py`、`transcode_profile.py`、`playlist_package.py` 定義資料類別。
- [x] T005 [P] 於 `backend/app/utils/settings.py` 實作組態載入與驗證（讀取 MG\_\* 環境變數並確保輸出路徑存在）。
- [x] T006 [P] 建立 `backend/app/services/progress_bus.py`，提供事件發布至 CLI 日誌與 REST 儲存的骨架（含 TTL 快取）。
- [x] T007 於 `backend/app/services/transcode_queue.py` 實作非同步佇列包裝器，限制同時 ffmpeg 工作 ≤2 並回報佇列深度。
- [x] T008 [P] 增加 `backend/app/services/output_manager.py`，負責建立／清理由 `output/{jobId}` 以及掛載壓縮中繼資料流程。
- [x] T009 建立共用測試腳手架（`backend/tests/conftest.py`），提供假進度匯流排與臨時輸出資料夾給後續故事使用。
- [x] T041 [P] 建立 `backend/app/services/retry_policy.py` 並於 `download_service.py`、`transcode_service.py` 掛上指數退避／錯誤分類，統一回傳 remediation（符合 FR-007）。
- [x] T049 [P] 強化 `backend/app/services/output_manager.py`，在建立目錄前檢查剩餘磁碟空間、必要時釋放暫存並回傳「釋出磁碟空間後重試」建議。
- [x] T050 [P] 新增 `backend/tests/unit/services/test_output_manager.py` 與 `backend/tests/integration/test_low_disk.py`，模擬磁碟不足／清理流程並驗證 remediation。

**檢查點**：在撰寫各使用者故事邏輯前，所有共用服務／模型／工具均可用。

---

## 第 3 階段：使用者故事 1 – CLI 提供行動友善的 YouTube 下載（優先度 P1）🎯 MVP

**目標**：CLI 透過 pytubefix 下載單支影片／播放清單、套用行動設定檔並輸出 ZIP 摘要。
**獨立驗證**：執行 `python -m app.cli.main download --url <yt_url> --format mp4`，應自動顯示進度並產生 ZIP 產物。

### 測試 – US1（實作前撰寫）

- [x] T010 [P] [US1] 在 `backend/tests/unit/services/test_download_service_youtube.py` 為 pytubefix 路由與備援旗標新增單元測試。
- [x] T011 [P] [US1] 於 `backend/tests/contract/test_cli_commands.py` 建立涵蓋 `download`、`playlist`、`status`、`retry` 指令的 CLI 契約測試。
- [x] T012 [P] [US1] 在 `backend/tests/integration/test_cli_youtube_pipeline.py` 撰寫整合測試（使用可控樣本或 stub）驗證產物與日誌。
- [x] T042 [P] [US1] 新增 CLI 節流／退避整合測試（模擬 HTTP 429 與平台錯誤），確認進度顯示退避倒數與 remediation。
- [x] T051 [P] [US1] 撰寫播放清單部分失敗案例測試，驗證 ZIP `SUMMARY.json` 會標示逐項狀態與錯誤建議。

### 實作 – US1

- [x] T013 [P] [US1] 在 `backend/app/services/download_service.py` 實作 YouTube 處理器（pytubefix 用戶端、播放清單切片、playlistItems 中繼資料）。
- [x] T014 [P] [US1] 建立 `backend/app/services/playlist_packager.py`，串流產生 ZIP、輸出 `SUMMARY.json` 與 `COMPRESSION_REPORT.txt`。
- [x] T015 [US1] 於 `backend/app/cli/main.py` 連線 `download/playlist/retry/status` 子指令並處理參數與 MG\_\* 環境變數。
- [x] T016 [US1] 將進度匯流排整合 CLI 日誌（`backend/app/cli/progress_renderer.py`），確保百分比單調遞增與佇列提示。
- [x] T017 [US1] 更新 `backend/TEST_RESULTS.md` 範本與自動化掛鉤，記錄 CLI 驗證（加入 YouTube 範例）。
- [x] T044 [US1] 將 `retry_policy` 併入 CLI 流程，於 `download_service.py` + `progress_renderer.py` 顯示退避倒數、剩餘嘗試與 remediation。
- [x] T052 [US1] 擴充 `playlist_packager.py` 與 CLI 摘要輸出，使部分成功的播放清單任務能清楚列出成功／失敗與建議。

**檢查點**：CLI 專注的 MVP 可運作，播放清單 ZIP 與進度事件皆通過驗證。

---

## 第 4 階段：使用者故事 2 – Web UI 支援非 YouTube 平台（優先度 P1）

**目標**：REST API 與前端可處理 Instagram/Facebook/X 下載，並具備備援轉檔與 cookies 流程。
**獨立驗證**：透過 `/api/downloads` 提交 Instagram Reel，應看到 `transcoding` 階段並下載到 ≤50MB 的行動版 MP4。

### 測試 – US2（實作前撰寫）

- [x] T018 [P] [US2] 在 `backend/tests/unit/services/test_download_service_social.py` 新增 yt-dlp 預設與 cookie 重試的單元測試。
- [x] T019 [P] [US2] 使用 `contracts/downloads.openapi.yaml` 於 `backend/tests/contract/test_downloads_api.py` 撰寫 `/api/downloads*` OpenAPI 契約測試。
- [x] T020 [P] [US2] 在 `backend/tests/integration/test_rest_social_pipeline.py` 實作 REST 整合測試（啟動本機 Flask + 模擬 ffmpeg 備援）。
- [ ] T021 [P] [US2] 於 `frontend/tests/App.downloads.test.ts` 撰寫前端組件測試（Vitest）以覆蓋進度主控台。
- [ ] T043 [P] [US2] 寫 REST 層節流／退避契約測試，模擬 429/5xx 並驗證 `/progress` 紀錄 queueDepth、retryAfter 與 remediation。

### 實作 – US2

- [ ] T022 [P] [US2] 擴充 `backend/app/services/download_service.py`，以 yt-dlp 預設處理 Instagram/Facebook/X（含 cookies 路徑、重試、節流）。
- [ ] T023 [P] [US2] 在 `backend/app/services/transcode_service.py` 呼叫佇列並強制主要／備援設定檔與檔案大小驗證。
- [x] T024 [US2] 建立 Flask blueprint `backend/app/api/downloads.py`，涵蓋 POST/GET/進度端點並串接進度匯流排與 playlistItems schema。
- [ ] T025 [US2] 於 `backend/app/api/request_validators.py` 新增 cookies 輸入與驗證（解碼 `cookiesBase64`、臨時儲存檔案）。
- [ ] T026 [US2] 更新 `frontend/src/lib/services/downloads.ts` 與 `frontend/src/App.svelte`，輪詢 `/progress`、呈現修復建議與佇列深度。
- [ ] T027 [US2] 在 `quickstart.md` 與 `README.md`（Web 章節）補完 REST 使用與 cookies 指引。
- [ ] T045 [US2] 將 `retry_policy` 結果映射到 REST 回應與前端訊息，確保 API payload 含 `retryAfterSeconds`、`attemptsRemaining`、 remediation。

**檢查點**：Web 使用者可下載 IG/FB/X 影片並獲得備援轉檔與前端可視化。

---

## 第 5 階段：使用者故事 3 – 營運人員監控統一管線健康度（優先度 P2）

**目標**：可觀測性與修復指引，提供一致的進度承載、佇列指標與建議。
**獨立驗證**：觸發任務後查詢 `/api/downloads/{jobId}/progress`，欄位與 CLI 輸出需一致。

### 測試 – US3（實作前撰寫）

- [ ] T028 [P] [US3] 在 `backend/tests/contract/test_progress_api.py` 為 `/api/downloads/{jobId}/progress` 新增契約測試，驗證 `status/stage/percent/queueDepth/queuePosition/remediation`。
- [ ] T029 [P] [US3] 於 `backend/tests/unit/services/test_remediation.py` 撰寫修復建議產生器與錯誤對應的單元測試。
- [ ] T030 [P] [US3] 在 `backend/tests/unit/utils/test_logging_format.py` 建立日誌回歸測試，確保結構化與人類可讀輸出。

### 實作 – US3

- [ ] T031 [P] [US3] 實作 `backend/app/services/progress_store.py`，維護 TTL 進度歷史與佇列指標並與匯流排整合。
- [ ] T032 [P] [US3] 在 `backend/app/services/remediation.py` 建立修復建議模組，對應 ffmpeg 缺失、節流、cookies 等錯誤碼。
- [ ] T033 [US3] 擴充 CLI 與 REST 回應，加入修復資訊與壓縮統計（更新 `backend/app/cli/progress_renderer.py`、`backend/app/api/downloads.py`）。
- [ ] T034 [US3] 自動化 `backend/TEST_RESULTS.md` 追加流程與產物壓縮報告腳本（`scripts/update_test_results.py`）。
- [ ] T035 [US3] 建立作業監控儀表與日誌設定（`backend/logs/logging.conf`）並於 `docs/observability.md` 說明操作步驟。

**檢查點**：營運可在 CLI/Web 取得一致遙測與修復訊息。

---

## 第 6 階段：潤飾與跨領域關注事項

- [ ] T036 [P] 強化錯誤翻譯與在地化掛鉤（`backend/app/services/remediation.py`），避免洩漏原始堆疊。
- [ ] T037 [P] 文件最終總整：更新 `quickstart.md`、`README.md`、`docs/` 圖表以反映統一管線架構。
- [ ] T038 [P] 效能巡檢：量測並行佇列情境、調整預設值、於 `docs/performance.md` 紀錄結果。
- [ ] T039 執行 `ruff check backend/` 與 `npm run lint`，於發佈前修正所有違規。
- [ ] T040 完整驗證 quickstart（CLI + Web）並將結果寫入 `docs/release-notes.md`。
- [ ] T046 [P] 建立 `scripts/run_cli_youtube_benchmarks.py`，自動連續執行 20 個 CLI YouTube 任務並輸出成功率／平均耗時，寫入 `backend/TEST_RESULTS.md`（SC-001）。
- [ ] T047 [P] 建立 `scripts/run_rest_social_benchmarks.py`，以 `/api/downloads` 模擬 IG/FB 下載並量測完成時間，確保 ≤120 秒並寫入測試紀錄（SC-002）。
- [ ] T048 [P] 擴充 `backend/TEST_RESULTS.md` 產出腳本，彙總 T046/T047 的統計並輸出 JSON/Markdown 報告供 CI 與文件引用。

---

## 相依與執行順序

1. **第 1 → 第 2 階段**：必須先完成設定，確保後續基礎服務的相依與環境文件就緒。
2. **第 2 → 第 3–5 階段**：共用模型／佇列／進度匯流排是每個使用者故事的前置條件。
3. **使用者故事順序**：完成第 2 階段後，先交付 US1（CLI）作為 MVP；US2（REST + 前端）可在 CLI 服務契約穩定後並行開發；US3 依賴前述遙測鉤子，但在匯流排 API 穩定後亦可並行。
4. **第 6 階段**：於需求使用者故事完成後執行。

## 平行化機會

- 帶有 `[P]` 的任務涉及不同檔案／模組，可同步進行（如測試與服務實作分流）。
- 自第 2 階段起，可讓不同開發者分別負責 US1（CLI）與 US2（REST/前端），並由第三人佈建 US3 可觀測性。
- 各故事的契約／整合測試可與服務骨架同步撰寫，只要鎖定不同檔案即可。

## 實作策略

1. **先完成 MVP**：交付第 1–3 階段，使 CLI YouTube 流程達到可上線水準，並驗證 SC-001/SC-003。
2. **漸進式釋出**：待 REST 與前端同質性就緒後交付 US2，並以真實 IG/FB 測試紀錄滿足 SC-002。
3. **營運強化**：實作 US3 以聚焦可觀測性／修復，符合 SC-003/SC-004 與營運需求。
4. **收尾潤飾**：第 6 階段專注文件、效能調校與 lint/測試關卡，再合併功能分支。
