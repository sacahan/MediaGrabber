---
post_title: MediaGrabber 專案憲章
author1: sacahan
post_slug: mediagrabber-constitution
microsoft_alias: sacahan
featured_image: https://github.com/user-attachments/assets/99ef6eaf-a6a2-43ef-b922-67d481daf400
categories: ["工具", "多平台", "下載器"]
tags: ["治理", "架構", "測試", "CLI", "Web", "Python", "Svelte"]
ai_note: 本文件由 AI 與專案擁有者共同編纂
summary: MediaGrabber 憲章定義專案不可被妥協的核心原則、技術標準與治理規範，並提供守門檢查清單以確保 CLI 與 Web 介面同步演進。
post_date: 2025-12-02
---

<!--
Sync Impact Report
Version: 1.0.0 → 1.1.0
Modified Principles:
- 雙介面等同可用（clarified parity scope and CLI/API alignment）
- 測試優先且涵蓋真實整合（explicit verification cadence）
- 設計簡潔、模組微小（codified ≤50 行限制）
Added Sections:
- 守門檢查（Constitution Gates）
- 版本與修訂政策
Removed Sections:
- None
Templates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md（無須更新）
- ✅ .specify/templates/tasks-template.md（無須更新）
Follow-ups:
- ✅ RATIFICATION_APPROVAL: approved by Brian Han on 2025-12-02
-->

# MediaGrabber 專案憲章

**專案定位**：多平台媒體下載工具
**核心目標**：以 CLI 與 Web 介面提供 YouTube、Facebook、Instagram、Twitter/X 等平台的高品質下載與後製流程

## 核心原則

### 一、雙介面等同可用

所有下載能力 MUST 同步支援 CLI 與 Web 介面，並保持輸入與輸出行為一致。

**理由**：使用者情境多元。CLI 服務自動化與批次流程，Web 則面向一般使用者；兩者需同樣強大且同步維護。

**實施要點**：

- CLI 指令 MUST 實作於現有 CLI 模組（目前為 `backend/media_grabber.py`，目標遷移至 `backend/app/cli/`），並提供完整參數解析與說明
- REST API MUST 由 Flask blueprint（`backend/app/api/`）提供，且對應 CLI 所有功能與參數
- 核心商業邏輯 MUST 集中在共享服務模組（目標路徑 `backend/app/services/`），未遷移的遺留程式需在 PR 中附遷移計畫
- 新功能開發順序 MUST 為：核心服務邏輯 → CLI 包裝 → API 端點，以確保共用程式碼
- 測試 MUST 驗證 CLI 與 Web 在輸出格式、品質選項與錯誤回報上完全等效

---

### 二、測試優先且涵蓋真實整合

單元測試使用模擬，整合測試則必須透過真實網路呼叫驗證各平台相容性。

**理由**：真正下載到的檔案必須可以播放。單靠模擬無法捕捉平台 API 變動、格式不相容或登入需求等問題。

**實施要點**：

- 測試程式碼 MUST 分佈於指定目錄層級，並在重構過程中持續將遺留測試搬遷至對應資料夾
- **單元測試**（`backend/tests/unit/`）：模擬 YoutubeDL、檔案 I/O 等外部依賴，專注於邏輯驗證
- **整合測試**（`backend/tests/integration/`）：使用實際平台 URL，下載至 `output/` 目錄並檢查是否能播放
- 整合測試 MUST 在每個 MINOR 發佈前以實際 URL 執行並記錄於 `backend/TEST_RESULTS.md`
- **契約測試**（`backend/tests/contract/`）：驗證 API 與 CLI 介面簽章一致
- **前端測試**（`frontend/tests/`）：單元測試 Svelte 元件與 API 整合
- **測試紀錄**：維護 `backend/TEST_RESULTS.md`，記錄各平台最新測試結果與限制
- **基本覆蓋**：每個次版號至少驗證一次 YouTube 單片、YouTube 播放清單、Facebook、Instagram、Twitter/X

---

### 三、設計簡潔、模組微小

避免過度抽象，優先採用責任明確、易於重構的直接實作。

**理由**：下載流程應維持「解析 URL → 取得資訊 → 下載 → （選擇性）轉碼」。引入過多工廠或管線會提高維護成本，日後更換下載庫（例：yt-dlp）也會更困難。

**實施要點**：

- 依平台或職責（下載 vs 轉碼）拆分模組，而非依設計模式分類，此規則 MUST 在新模組中立即遵循
- 函式長度 MUST ≤ 50 行；若無法拆分，PR 必須附帶重構計畫並於同版次完成拆分
- 非必要不得新增「Manager」「Handler」等控制類別，除非協調三個以上元件
- 結構化資料 MUST 採用 dataclass（如 DownloadJob、ProgressState），避免冗長 getter/setter 類別

---

### 四、品質優化採漸進策略

先確保下載成功，再以選配流程提供轉檔與行動裝置最佳化。

**理由**：下載是最核心任務；轉碼（例如 MP3 萃取、行動化檔案）屬於加值功能。分階段實作能降低耦合並易於維護。

**實施要點**：

- **核心下載**：MUST 直接輸出平台原始檔（可能是 m4a、webm 等）
- **格式轉換**（m4a → MP3）：MUST 以 ffmpeg 後處理並保持可配置
- **行動轉碼**（檔案大小／位元率最佳化）：MUST 維持獨立管線並透過參數啟用
- 每一階段 MUST 保留中間產物，允許獨立使用或串接

---

### 五、可觀測且易於閱讀

所有流程必須輸出人類可讀的進度與錯誤資訊，方便 CLI 與 Web 顯示。

**理由**：使用者需要知道目前進度、剩餘時間、錯誤原因。純結構化日誌（JSON）不符合互動需求。

**實施要點**：

- 進度回呼需回傳 `status`、`stage`（描述）、`percent`、`downloaded_bytes`、`total_bytes`、`speed`、`eta`
- 錯誤訊息需包含根本原因、建議行動（如「稍後再試」「檢查 URL」）與平台注意事項
- 目前統一使用英文訊息；多語系支援列為未來工作
- 禁止靜默失敗，所有流程需明確回報成功或失敗

---

## 守門檢查（Constitution Gates）

以下守門條件 MUST 在 `/speckit.plan` 產出的實作計畫啟動前完成自我檢查，未通過者禁止進入 Phase 0。

- **Gate MG-G1 — 雙介面等同可用**
  - PASS：規劃列出 CLI 指令與 REST API 端點的同步更新，並安排等效測試。
  - FAIL：缺少任一介面或測試、僅描述其中一端的流程。
- **Gate MG-G2 — 真實整合驗證**
  - PASS：識別所需的真實 URL、網路限制與驗證時點，並在任務中安排記錄結果。
  - FAIL：僅依賴模擬或未規劃結果紀錄。
- **Gate MG-G3 — 模組邊界與複雜度**
  - PASS：說明服務模組拆分、函式長度控制與避免非必要控制類別的策略。
  - FAIL：以「日後重構」為由忽略複雜度或持續堆疊臨時管理類。
- **Gate MG-G4 — 漸進式品質策略**
  - PASS：計畫先交付可用下載，再排程轉碼或裝置優化；可選功能標示為 opt-in。
  - FAIL：核心下載依賴選配功能或缺乏還原計畫。
- **Gate MG-G5 — 可觀測性**
  - PASS：明確列出進度與錯誤訊息欄位，以及 CLI 與前端呈現方式。
  - FAIL：僅記錄結構化日誌或無人類可讀輸出。

## 技術標準

### 技術堆疊（固定）

- **後端**：Python 3.12+、Flask 2.0+、PEP 8 MUST 遵循
- **前端**：Svelte 5、Vite 6、Tailwind CSS、Typescript MUST 作為預設堆疊
- **媒體函式庫**：yt-dlp（多平台）、pytubefix（YouTube 專用）、ffmpeg 4.0+（轉碼）MUST 保持最新相容版本
- **程式品質**：使用 ruff、pre-commit，所有公開函式 MUST 具備型別註解
- **測試工具**：pytest（Python）、unittest.mock、Vitest（前端）以及真實網路整合測試；執行結果 MUST 記錄於 `backend/TEST_RESULTS.md`

### 架構基線（強制遵循）

所有服務、介面與測試程式必須依下列結構組織；既有模組需透過重構與遷移在迭代中達成此基線。

```text
project/
│
├─ backend/                       # Python 後端
│   ├─ app/                       # 主程式碼
│   │   ├─ api/                   # API 路由
│   │   ├─ services/              # 商業邏輯
│   │   ├─ models/                # 資料模型
│   │   └─ utils/                 # 工具函式
│   │
│   ├─ tests/                     # 測試程式碼
│   │   ├─ unit/
│   │   ├─ integration/
│   │   └─ contract/
│   │
│   ├─ requirements.txt
│   └─ main.py
│
├─ frontend/                      # 前端（Svelte）
│   ├─ src/
│   ├─ tests/                     # 測試程式碼
│   ├─ public/
│   └─ package.json
│
├─ infra/                         # Infrastructure（可選）
│   ├─ docker/
│   └─ scripts/
│
├─ docker-compose.yml
└─ README.md
```

### 平台支援狀態

| 平台                | 格式     | 函式庫            | 狀態    | 備註                         |
| ------------------- | -------- | ----------------- | ------- | ---------------------------- |
| YouTube（單支影片） | MP3、MP4 | pytubefix 10.3.5+ | ✅ 已測 | 播放清單以個別任務處理       |
| YouTube（播放清單） | MP3、MP4 | pytubefix 10.3.5+ | ✅ 已測 | 逐一下載，預設延遲 3 秒      |
| Facebook            | MP4      | yt-dlp 2025+      | ✅ 已測 | 免登入（可選擇提供 cookies） |
| Instagram           | MP4      | yt-dlp 2025+      | ✅ 已測 | 約 5–10 次後可能遇到節流     |
| Instagram（Reel）   | MP4      | yt-dlp 2025+      | ✅ 已測 | 約 5–10 次後可能遇到節流     |
| Twitter/X           | MP4      | yt-dlp 2025+      | ✅ 已測 | 支援影片，不含 GIF           |

---

## 開發流程

### 功能開發序列（強制遵循）

每項功能、修正或重構必須依序完成下列工作項，禁止跳步或並行跳過驗證：

1. ✅ 於 `backend/app/services/` 實作核心邏輯
2. ✅ 撰寫單元測試（`backend/tests/unit/`）並模擬外部依賴
3. ✅ 補齊 CLI 指令（`backend/main.py` 參數解析）
4. ✅ 新增 REST API 端點（`backend/app/api/` 路由）
5. ✅ 撰寫整合測試（`backend/tests/integration/`）驗證平台相容性
6. ✅ 撰寫契約測試（`backend/tests/contract/`）確保介面一致
7. ✅ 更新 README.md（中英文）說明
8. ✅ 若平台支援狀態改變，更新 TEST_RESULTS.md
9. ✅ 執行 `ruff check backend/` 與 pre-commit
10. ✅ 產生文件使用正體中文表示
11. ✅ 程式碼注釋使用正體中文撰寫

### 核心下載邏輯調整

1. 保留相容性：既有 URL 必須仍可使用
2. 新增參數需為選用，並提供合理預設值
3. 對所有平台重新進行整合測試
4. 若不可避免有破壞性變更：提升次版號並撰寫遷移指南

---

## 治理規範

**憲章優先**：任何偏離本文件的作法皆需在 PR 與提交訊息中記錄理由。

**修訂流程**：

1. 撰寫提案與理由說明
2. 取得專案擁有者（Brian Han）核准
3. 於下方〈版本紀錄〉新增條目
4. 同步更新關聯文件（CLAUDE.md、GEMINI.md、README.md）

**遵循檢查**：每次發佈需檢視所有 PR 是否符合原則；若有違規，需延後佈署或先行重構，核心下載流程不得累積技術債。

---

### 版本與修訂政策

- **MAJOR**：移除或改寫核心原則、治理流程或守門條件屬於破壞性變更，需同步制定遷移指南。
- **MINOR**：新增原則、擴充守門條件或引入強制性治理步驟。
- **PATCH**：措辭澄清、錯字修正或補充範例，不得改變合規要求。
- 每次修訂 MUST 更新本文頂部的 Sync Impact Report 並同步檢查 `.specify/templates/` 相關模板。

---

## 版本紀錄

| 版本  | 日期       | 變更內容                          | 狀態           |
| ----- | ---------- | --------------------------------- | -------------- |
| 1.1.0 | 2025-12-02 | 守門檢查、測試節奏、模組規範強化  | ✅ 已核准      |
|       |            | - 新增 Constitution Gates         |                |
|       |            | - 明確整合測試頻率與記錄要求      |                |
|       |            | - 強化 CLI/API 對應與函式長度限制 |                |
| 1.0.0 | 2025-12-02 | 初版憲章草稿                      | 草稿（待審核） |
|       |            | - 雙介面等同可用                  |                |
|       |            | - 測試優先含真實整合              |                |
|       |            | - 設計簡潔模組微小                |                |
|       |            | - 品質優化採漸進策略              |                |
|       |            | - 可觀測且易於閱讀                |                |

**版本**：1.1.0 | **核准日期**：2025-12-02 | **最後修訂**：2025-12-02
