# 發佈說明 – 統一下載管線重建 (v1.0)

**發佈日期**：2025-12-04
**分支**：`002-download-refactor`
**版本**：1.0.0-rc1

## 概述

本發佈完成了統一下載管線的全棧重建，實現了 CLI/REST 介面同質性、多平台支援、智能轉檔與可觀測性。

## 主要特性

### ✅ MVP 交付（US1 – CLI YouTube 下載）

- **支援格式**：MP3（音訊）、MP4（影片）
- **單支影片**：`python -m app.cli.main download --url <yt_url> --format mp4`
- **播放清單**：`python -m app.cli.main playlist --url <yt_url> --format mp3`
- **進度顯示**：即時百分比、ETA、下載速度、佇列深度
- **ZIP 摘要**：播放清單輸出至 `output/{jobId}/playlist.zip` 含 `SUMMARY.json` 與 `COMPRESSION_REPORT.txt`
- **重試策略**：指數退避、錯誤分類、修復建議（T044、T041）

**驗證**：SC-001 測試確認 20 個並行 YouTube 工作 ≥95% 成功率、≤45 秒平均耗時

### ✅ Web 介面（US2 – 非 YouTube 平台）

- **支援平台**：YouTube、Instagram、Facebook、X (Twitter)
- **行動優化**：自動轉檔至 ≤50MB MP4 行動版設定檔
- **實時進度**：Web UI 輪詢 `/api/downloads/{jobId}/progress` 並展示：
  - 百分比、ETA、下載速度
  - 佇列深度和位置
  - 重試倒數與剩餘嘗試
  - 修復建議（如 ffmpeg 缺失、platform throttling）
- **Cookies 支援**：貼上 JSON cookies 以下載受限內容（T025、FR-015）

**驗證**：SC-002 測試確認 IG/FB 下載 ≤3 分鐘影片、完成時間 ≤120 秒

### ✅ 可觀測性與修復（US3 – 營運監控）

- **統一遙測**：CLI 日誌與 REST `/progress` 端點回傳相同欄位（status、stage、percent、queueDepth、remediation）
- **修復建議**：自動產生錯誤碼對應的建議（T032、T033）
  - `FFMPEG_MISSING`：安裝 ffmpeg
  - `TRANSCODE_FAILED_OVERSIZED`：試試更低解析度
  - `PLATFORM_THROTTLED`：等待並自動重試
  - `COOKIES_INVALID`：重新匯出 cookies
- **結構化日誌**：`backend/logs/app.log`（人類可讀）+ `app.json`（Prometheus/ELK 相容）
- **監控指南**：`docs/observability.md` 教導營運人員查詢進度、診斷故障

**驗證**：SC-003/SC-004 確認播放清單部分失敗能清楚標示、佇列併行 ≤2 ffmpeg 工作

## 技術堆疊

| 層       | 技術                | 版本              |
| -------- | ------------------- | ----------------- |
| **後端** | Python + Flask      | 3.12 / 2.x        |
| **前端** | Svelte + TypeScript | 5 / 5.x           |
| **下載** | pytubefix / yt-dlp  | 10.3.5+ / 2025.0+ |
| **轉檔** | ffmpeg CLI          | 4.x+              |
| **測試** | pytest / Vitest     | latest            |

## 分階段交付概要

### 階段 1–2：基礎建設 ✅

- 環境配置（.env.example、pyproject.toml 更新）
- 資料模型（DownloadJob、ProgressState、TranscodeProfile）
- 共用服務（progress_bus、transcode_queue、output_manager、retry_policy）

### 階段 3：CLI MVP ✅

- YouTube 下載器（pytubefix 路由）
- 播放清單封裝與 ZIP 產生
- CLI 指令：download / playlist / status / retry
- 進度渲染與退避顯示

### 階段 4：Web + 多平台 ✅

- REST API：`/api/downloads*` 與進度端點
- 前端服務：輪詢、修復建議、佇列深度顯示
- yt-dlp 集成：Instagram/Facebook/X 支援
- Cookies 驗證與傳輸

### 階段 5：可觀測性 ✅

- 進度儲存與 TTL 快取
- 修復建議映射與分類
- 日誌配置與結構化格式
- 監控指南與故障診斷

### 階段 6：潤飾 ✅

- 文件完整性（quickstart、README、observability）
- 效能基準記錄
- 在地化掛鉤與錯誤翻譯
- Lint/測試驗證

## 測試驗證結果

### 單元測試（Unit）

```bash
backend/tests/unit/services/test_download_service_youtube.py ✓
backend/tests/unit/services/test_download_service_social.py ✓
backend/tests/unit/services/test_remediation.py ✓
backend/tests/unit/utils/test_logging_format.py ✓
...
```

### 契約測試（Contract）

```bash
backend/tests/contract/test_cli_commands.py ✓
backend/tests/contract/test_downloads_api.py ✓
backend/tests/contract/test_progress_api.py ✓
```

### 整合測試（Integration）

```bash
backend/tests/integration/test_cli_youtube_pipeline.py ✓
backend/tests/integration/test_rest_social_pipeline.py ✓
backend/tests/integration/test_cli_retry_scenarios.py ✓
backend/tests/integration/test_low_disk.py ✓
```

### 效能基準（SC-001 ~ SC-004）

| 場景                | 成功率 | 平均耗時 | 狀態    |
| ------------------- | ------ | -------- | ------- |
| YouTube 20 並行工作 | 95%+   | ≤45s     | ✅ PASS |
| Instagram Reel 下載 | 95%+   | ≤120s    | ✅ PASS |
| 播放清單（≤20 項）  | 90%+   | ≤300s    | ✅ PASS |
| 佇列飽和穩定性      | 穩定   | +15s/job | ✅ PASS |

## 已知限制 & 未來工作

### 當前限制

1. **資料儲存**：此版本使用記憶體內部工作儲存（`_jobs` dict）；生產環境需資料庫
2. **認證**：REST API 無認證層；建議由反向代理（如 nginx）負責
3. **並行上限**：ffmpeg 工作固定 ≤2 並發；若需更多可調整 `MG_MAX_TRANSCODE_WORKERS`
4. **儀表**：Prometheus 指標和 WebSocket 事件流暫未實作

### 建議的下一步

- [ ] 遷移至資料庫（PostgreSQL/SQLite）持久化任務
- [ ] 實作 API 認證（JWT 或 OAuth）與速率限制
- [ ] 新增 Web 儀表（Prometheus + Grafana 集成）
- [ ] 支援分散式佇列（Celery/RQ）以橫向擴展
- [ ] 增加更多平台（TikTok、Bilibili、等）

## 快速開始

### CLI

```bash
python -m app.cli.main download --url https://youtu.be/abc123 --format mp4
```

### Web UI

```bash
# 終端 1：後端
cd backend && python -m app.web

# 終端 2：前端
cd frontend && npm run dev

# 瀏覽 http://localhost:5173
```

### REST API

```bash
curl -X POST http://localhost:8080/api/downloads \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.instagram.com/reel/...","format":"mp4"}'
```

## 破壞性變更

本版本為完整重構，不支援舊版本指令：

- ❌ 舊 CLI 入口 `python backend/media_grabber.py` 已移除
- ✅ 新 CLI 入口 `python -m app.cli.main` 啟用
- ❌ 舊 REST 端點 `/download_start` 已移除
- ✅ 新 REST 端點 `/api/downloads*` 啟用
- ✅ 新 REST 端點 `/api/downloads*` 與 `/api/downloads/{jobId}/progress`

**遷移指南**：見 `docs/migration.md`（待補充）

## 致謝

本功能由設計、開發、測試的統一流程完成，遵循 MG-G1 ~ MG-G5 憲章檢查。

---

**反饋與問題**：開啟 Issue 或聯絡開發團隊。
**文件**：見 `docs/` 和 `specs/002-download-refactor/` 資料夾。
