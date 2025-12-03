# 可觀測性與操作指南

## 概述

統一下載管線提供了多層的可觀測性機制，讓營運人員能夠即時監控任務狀態、排隊情況、以及故障診斷。本文件說明如何使用 CLI、REST API、日誌，以及佇列儀表。

## 日誌設定

### 結構化日誌

日誌存放在 `backend/logs/` 底下：

- **`app.log`**：人類可讀的純文字日誌（INFO 級別及以上）
- **`app.json`**：結構化 JSON 日誌（DEBUG 及以上），便於 ELK/Splunk 等聚合

### 啟用日誌

編輯 `backend/media_grabber_web.py` 並加載日誌配置：

```python
import logging.config
logging.config.fileConfig('backend/logs/logging.conf')
logger = logging.getLogger(__name__)
```

### 日誌查詢範例

**查看最新 100 行下載進度**：

```bash
tail -100 backend/logs/app.log | grep -E "DOWNLOADING|TRANSCODING"
```

**查看特定任務的完整流程**：

```bash
JOB_ID="<jobId>"
grep "$JOB_ID" backend/logs/app.json | jq '.'
```

## REST API 進度端點

### `/api/downloads/{jobId}/progress` 回應

實時進度查詢返回以下欄位：

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

### 輪詢最佳實踐

**建議輪詢間隔**：1–2 秒（避免後端過載）

```bash
# 每秒輪詢直到完成
while true; do
  curl -s http://localhost:8080/api/downloads/$JOB_ID/progress | jq '.status'
  [ "$(curl -s http://localhost:8080/api/downloads/$JOB_ID/progress | jq -r '.status')" = "completed" ] && break
  sleep 1
done
```

## CLI 佇列監控（計劃中）

未來版本將支持：

```bash
python -m app.cli.main queue
```

輸出：

```
Active Jobs:
  [DOWNLOADING] 45% - youtube.com/watch?v=abc (ETA: 15s)
  [QUEUED]      0%  - instagram.com/reel/xyz (waiting for ffmpeg)

Queue Depth: 2 / 2 workers
Worker Status:
  Worker 1: transcoding (3 / 4 completed)
  Worker 2: idle
```

## 修復建議（Remediation）

當任務遇到可恢復的錯誤時，REST 與 CLI 會返回 `remediation` 物件。

### 常見建議碼

| 碼                           | 訊息                 | 建議                                  | 分類           |
| ---------------------------- | -------------------- | ------------------------------------- | -------------- |
| `FFMPEG_MISSING`             | ffmpeg 未找到        | 安裝 ffmpeg 4.x 並加入 PATH           | `system_issue` |
| `TRANSCODE_FAILED_OVERSIZED` | 轉碼後檔案超過 50MB  | 試試更低解析度或檢查 ffmpeg           | `retry`        |
| `PLATFORM_THROTTLED`         | 平台回傳 HTTP 429    | 等待並重試（已自動排程）              | `retry`        |
| `COOKIES_INVALID`            | Cookies 已過期或無效 | 重新匯出並上傳最新 cookies            | `user_action`  |
| `PLAYLIST_PARTIAL_FAIL`      | 播放清單部分項目失敗 | 查看 ZIP 內 SUMMARY.json 了解個別狀態 | `user_action`  |

## 監控儀表（未來）

計劃新增 Web 儀表，實時展示：

- **全域統計**：今日下載數、成功率、平均速度
- **活躍任務清單**：正在進行的工作、ETA、進度
- **佇列深度圖表**：ffmpeg 工作數隨時間變化
- **失敗任務追蹤**：錯誤代碼分佈、建議統計
- **效能指標**：網路吞吐量、轉檔耗時分佈

## 故障診斷

### 症狀 1：任務卡在 `DOWNLOADING` 階段

**可能原因**：網路連線問題或平台限流

**診斷**：

```bash
# 檢查平台回應
curl -I https://www.youtube.com/watch?v=...
# 查看日誌是否有 429 或連線超時
grep "429\|timeout\|THROTTLED" backend/logs/app.log
```

**建議**：檢查網路、等待後重試（系統會自動排程指數退避）

### 症狀 2：轉檔失敗，檔案超大

**可能原因**：行動設定檔無法以 ≤50MB 編碼

**診斷**：

```bash
# 檢查轉檔日誌
grep "TRANSCODE_FAILED_OVERSIZED" backend/logs/app.json | jq '.message'
```

**建議**：試試更低位元率或備援編碼器；檢查 ffmpeg 版本 ≥4.0

### 症狀 3：Cookies 認證失敗

**可能原因**：Cookies 已過期或格式錯誤

**診斷**：

```bash
# 檢查 cookies 驗證日誌
grep "COOKIES_INVALID\|auth" backend/logs/app.json | jq '.'
```

**建議**：在瀏覽器重新匯出最新 cookies，確保格式為 JSON

## 效能基準

### 基線指標（SC-001 ~ SC-004）

| 場景                           | 成功率 | 平均耗時  | 備註                   |
| ------------------------------ | ------ | --------- | ---------------------- |
| CLI YouTube 單支（10 分鐘）    | ≥95%   | ≤45s      | SC-001: 20 個並行工作  |
| REST Instagram Reel（≤3 分鐘） | ≥95%   | ≤120s     | SC-002: 含轉檔至 ≤50MB |
| 播放清單（≤20 項）             | ≥90%   | ≤300s     | SC-003: 允許部分失敗   |
| 佇列飽和（≥5 工作）            | 穩定   | +15s/工作 | SC-004: 線性降解       |

## 營運檢查清單

每週或定期執行：

- [ ] 檢查 `backend/logs/app.log` 是否有異常（Error、警告堆積）
- [ ] 執行 `scripts/update_test_results.py` 驗證基線是否達成
- [ ] 確認 ffmpeg 版本 ≥4.0 且在 PATH 上
- [ ] 確認磁碟空間充足（建議 ≥5GB 可用）
- [ ] 檢查 Cookies 池是否需更新（Instagram/Facebook 每月一次）

## 進階：自訂儀表整合

### 以 Prometheus 格式匯出指標

計劃支持 `/metrics` 端點輸出 Prometheus 格式，便於 Grafana 集成。

預期指標：

```
mediagrabber_jobs_total{status="completed"} 150
mediagrabber_jobs_total{status="failed"} 5
mediagrabber_queue_depth 2
mediagrabber_transcode_worker_busy 2
mediagrabber_download_speed_mbps 5.2
```

### 事件流（計劃中）

支持 WebSocket 訂閱任務事件流，便於即時儀表更新：

```
ws://localhost:8080/api/jobs/events
```

事件類型：`job_started`、`progress_updated`、`job_completed`、`job_failed`
