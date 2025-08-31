---
post_title: MediaGrabber 中文說明
author1: sacahan
post_slug: mediagrabber-zh
microsoft_alias: sacahan
featured_image: https://github.com/user-attachments/assets/99ef6eaf-a6a2-43ef-b922-67d481daf400
categories: ["工具", "多平台", "下載器"]
tags: ["YouTube", "Facebook", "Instagram", "Docker", "Svelte", "Python"]
ai_note: 部分內容由 AI 協助翻譯
summary: MediaGrabber 是一款支援多平台的 Python 下載工具，支援 CLI 與 Web GUI，並可透過 Docker 快速部署。
post_date: 2025-08-31
---

# MediaGrabber

一款簡單的 Python 下載器：

- **YouTube → MP3/MP4**，支援命令列與網頁介面（可選格式）
- **Facebook → MP4**、**Instagram → MP4**，支援網頁介面（單檔 50MB 限制）

![demo](https://github.com/user-attachments/assets/99ef6eaf-a6a2-43ef-b922-67d481daf400)

## 使用方式

本專案可分為兩種模式：**Docker**（適合正式環境）與 **開發模式**（本地測試與開發）。

### Docker 模式

支援多平台 Docker 建置與推送，建議使用 `scripts/deploy.sh` 進行 production-like 部署。

#### 多平台建置與推送

執行 `scripts/deploy.sh` 會：

1. 建立/使用 buildx builder，支援 `linux/amd64, linux/arm64` 多平台。
2. 透過 `--build-arg VITE_API_BASE_URL=...` 傳遞 API base url 給前端（預設 `https://media.brianhan.cc`，可自訂）。
3. 建置並推送 image 至 Docker Hub（不保留本地 image）。

範例：

```bash
cd scripts
./deploy.sh # 使用預設 API base url
./deploy.sh https://api.example.com # 指定 API base url
```

`deploy.sh` 會自動將 `VITE_API_BASE_URL` 以 build-arg 傳入 Docker build，確保前端 SPA 連線正確。

推送完成後，image 會在 Docker Hub 上的 `sacahan/media-grabber:latest`。

#### 停止與移除容器

```bash
docker stop mediagrabber && docker rm mediagrabber
```

---

#### 備註

- `scripts/deploy.sh` 主要用於多平台建置與推送，若只需本地測試可參考 `build_and_run.sh`。
- 若需自訂 buildx builder 名稱、平台或其他參數，可直接編輯 `deploy.sh`。

### Scripts 腳本

專案內建 `scripts/` 目錄，包含：

- `deploy.sh`：多平台 Docker 建置與推送，支援 build-arg 傳遞 API base url。
- `startup.sh`：可用於自動啟動服務或初始化環境（請依實際內容補充用途）。

建議所有部署、建置相關操作都透過 scripts 目錄下的腳本執行。

### 開發模式

開發模式下，前端與後端分開執行，支援熱重載與除錯。

#### 1. 後端 API（Flask）

進入 `backend` 目錄並啟動 Flask 應用：

```bash
cd backend
python media_grabber_web.py
```

API 會在 `http://localhost:8080` 運行，日誌儲存於 `backend/log/flask.log`。
**注意：** Flask 為 WSGI 應用，Uvicorn 主要用於效能提升，若需完整 async 支援建議改用 FastAPI 或 Starlette。

#### 2. 前端（Svelte + Tailwind CSS）

進入 `frontend` 目錄並啟動 Svelte 開發伺服器：

```bash
cd frontend
npm run dev
```

前端通常運行於 `http://localhost:5173`（或其他可用 port），可直接於瀏覽器開啟。

#### 3. 命令列下載

透過腳本下載音訊或影片：

```bash
cd backend
source .venv/bin/activate # 啟用虛擬環境
python media_grabber.py <URL> [-f FORMAT] [-o OUTPUT_DIR]
```

選項：

- `-f, --format`：`mp3`（音訊）或 `mp4`（影片），預設 `mp3`
- `-o, --output`：輸出目錄（預設 `../output`）

範例：

- 下載 YouTube 音訊 MP3 至專案根目錄 output

```bash
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp3 -o ../output
```

- 下載 YouTube 影片 MP4 至自訂目錄

```bash
cd backend
source .venv/bin/activate
python media_grabber.py https://youtu.be/abc123 -f mp4 -o /path/to/your/videos
```

- 下載 Facebook 影片 MP4

```bash
cd backend
source .venv/bin/activate
python media_grabber.py https://facebook.com/... -f mp4
```

## 開發環境

### 需求

- Python 3.7 以上
- Node.js（建議 LTS）與 npm
- `ffmpeg` 已安裝並在 PATH
- macOS 可用下列指令抑制 Tk 警告：

  ```bash
  export TK_SILENCE_DEPRECATION=1
  ```

### 專案結構

```txt
MediaGrabber/
├── backend/             # Flask REST API 與 Python 核心邏輯
│   ├── media_grabber.py
│   ├── media_grabber_web.py
│   ├── pyproject.toml   # Python 依賴設定
│   ├── .venv/           # Python 虛擬環境
│   ├── __pycache__/
│   └── log/             # Flask 應用日誌
├── frontend/            # Svelte SPA + Tailwind CSS
│   ├── node_modules/
│   ├── public/
│   ├── src/
│   ├── .gitignore
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── svelte.config.js
│   ├── tailwind.config.js # Tailwind CSS 設定
│   └── vite.config.js
├── output/              # 下載檔案預設目錄
├── scripts/             # 部署與啟動腳本（deploy.sh, startup.sh）
├── .gitignore
├── LICENSE
└── README.md
```

### 後端安裝

進入 `backend` 目錄並使用 `uv` 安裝 Python 依賴：

```bash
cd backend
# 若未安裝 uv，請先執行
pip install uv

# 自動建立虛擬環境並安裝依賴
uv sync
cd .. # 回到專案根目錄
```

### 前端安裝

進入 `frontend` 目錄並安裝 Node.js 依賴：

```bash
cd frontend
npm install
cd .. # 回到專案根目錄
```

### FFmpeg 安裝

macOS 可用 Homebrew 安裝：

```bash
brew install ffmpeg
```

Windows 可用：

- **Chocolatey**：`choco install ffmpeg`
- **Scoop**：`scoop install ffmpeg`
- **手動**：至 [ffmpeg.org](https://ffmpeg.org/download.html#build-windows) 下載並加入 PATH

Linux（Ubuntu/Debian）：

```bash
sudo apt update
sudo apt install ffmpeg
```

Linux（CentOS/RHEL/Fedora）：

```bash
# CentOS/RHEL
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```
