# 實作計畫：統一下載管線重建

**分支**：`[002-download-refactor]` | **日期**：2025-12-03 | **規格**：`/specs/002-download-refactor/spec.md`
**輸入**：來自 `/specs/002-download-refactor/spec.md` 的功能規格

**備註**：此模板由 `/speckit.plan` 指令自動產生。執行流程請參閱 `.specify/templates/commands/plan.md`。

## 摘要

重新打造媒體下載管線，讓 CLI（`python -m app.cli.main`）與 REST（`/api/downloads*`）共享同一套服務層：`download_service.py` 依網址路由至 pytubefix（YouTube）或 yt-dlp（其他平台），`transcode_service.py` 透過全域雙槽 ffmpeg 佇列執行行動裝置主要／備援設定檔，並以統一的進度遙測餵給營運人員與前端。兩種介面皆公開相同的平台／格式矩陣（YouTube MP4/MP3、Instagram/Facebook/X 行動版 MP4）以符合憲章 MG-G1。輸出隔離（`output/{jobId}`）、播放清單封裝、重試政策以及真實場景測試記錄（`backend/TEST_RESULTS.md`）確保新管線滿足 SC-001–SC-004。

## 技術背景

**語言／版本**：後端 Python 3.12 + Flask 2.x；前端 Svelte 5 + TypeScript；媒體處理使用 ffmpeg 4.x。
**主要相依**：pytubefix 10.3.5+、yt-dlp 2025.0+、ffmpeg CLI、click/argparse（CLI 入口）、Vite、Tailwind CSS。
**儲存**：`output/{jobId}` 底下的本機檔案系統與暫存資料夾；此迭代不引入資料庫。
**測試**：pytest（單元、整合、契約）、前端使用 Vitest，另需於 `backend/TEST_RESULTS.md` 紀錄手動／自動的真實網址測試。
**目標平台**：具備 ffmpeg 與網路出口的 Linux/macOS 主機；前端由 Node/Vite 開發伺服器與靜態主機提供。
**專案型態**：後端 Flask 服務 + Svelte SPA 的分離式 Web 應用並共享服務模組。
**效能目標**：滿足 SC-002（≤120 秒處理 ≤3 分鐘的 IG/FB 影片）、維持 20 個 YouTube 工作 ≥95% 成功率（SC-001）、佇列並行 ffmpeg ≤2 以避免壓垮 CPU。
**限制**：函式 ≤50 行、REST 為匿名存取（節流由基礎設施負責）、僅在主要輸出違反大小／位元率時啟用備援轉檔、進度百分比需單調遞增、必須維持 CLI/網頁同質性。
**規模／範圍**：數十個同時下載工作並排隊轉檔，涵蓋 YouTube/Instagram/Facebook/X 平台；含三個核心使用者故事與營運可觀測性。

## 憲章檢查

_門檻：Phase 0 研究前必須通過，Phase 1 設計後再次確認。_

- [x] **Gate MG-G1 — 介面同質性**：CLI 指令（`download`、`playlist`、`retry`、`status`）與 REST 端點（`/api/downloads`、`/api/downloads/{jobId}`、`/api/downloads/{jobId}/progress`）將共用服務並同步撰寫對應測試。
- [x] **Gate MG-G2 — 真實世界驗證**：計畫為各平台記錄實際網址、強制重試，並要求在發佈前把所有手動／整合測試寫入 `backend/TEST_RESULTS.md`。
- [x] **Gate MG-G3 — 模組邊界**：服務僅限於既定檔案（`download_service.py`、`transcode_service.py`、播放清單封裝器），輔助函式 ≤50 行並使用 `DownloadJob`／`ProgressState` 資料類別；不新增管理類別。
- [x] **Gate MG-G4 — 漸進式品質**：流程先下載原始檔、即刻提供產出，再依需求透過選用旗標與佇列語意啟動行動版／備援轉檔。
- [x] **Gate MG-G5 — 可觀測性**：進度承載 `status`、`stage`、`percent`、`downloadedBytes`、`totalBytes`、`speed`、`etaSeconds`、`message`，並透過 CLI 日誌與 `/progress` 端點加上修復建議呈現。

_2025-12-03 複驗_：Phase 1 成果（`data-model.md`、`contracts/downloads.openapi.yaml`、`quickstart.md`）再次強化各門檻：實體定義維持服務邊界精簡（MG-G3）、OpenAPI 映射 CLI 能力（MG-G1）、快速上手／測試章節固化真實網址驗證與漸進／備援行為（MG-G2/MG-G4/MG-G5）。

## 專案結構

### 文件（此功能）

```text
specs/002-download-refactor/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md（由 /speckit.tasks 產生）
```

### 原始碼（版本庫根目錄）

```text
backend/
├── app/
│   ├── api/               # Flask 藍圖（新 downloads 藍圖位於此）
│   ├── cli/               # CLI 入口 `app/cli/main.py`
│   ├── services/          # download_service.py、transcode_service.py、播放清單封裝
│   ├── models/            # DownloadJob、ProgressState、TranscodeProfile 資料類別
│   └── utils/
├── tests/
│   ├── unit/              # 服務向的 pytest 測試
│   ├── integration/       # 真實網址下載／轉檔驗證
│   └── contract/          # CLI 與 REST 對照測試
└── media_grabber_web.py   # Flask 應用啟動點

frontend/
├── src/
│   ├── lib/               # 共用 store／服務
│   ├── assets/
│   └── App.svelte         # 消費 `/api/downloads` 的下載面板
├── public/
└── tests/（將以 Vitest 擴充）

output/                    # 由服務管理的工作產物
scripts/                   # 部署輔助腳本
```

**結構決策**：維持前後端分離，服務放在 `backend/app/services/` 並於 `backend/tests/*` 撰寫對應測試；Svelte SPA（`frontend/src`）消費新的 REST 端點；此功能相關文件集中於 `specs/002-download-refactor/`。

## 複雜度追蹤

> **僅在憲章檢查有違規且需說明時填寫**

| 違規 | 原因 | 為何拒絕更簡方案 |
| ---- | ---- | ---------------- |
| _無_ |      |                  |
