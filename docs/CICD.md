# MediaGrabber CI/CD 指南

本展示使用 Gitea Actions 實現 MediaGrabber 的自動建置與部署。

## 部署流程
1. **觸發**: 當程式碼推送到 `main` 或 `master` 分支,或手動點擊工作流程。
2. **建置**: 
   - 讀取 `VITE_API_BASE_URL` secret。
   - 在 Gitea Runner 所在環境建置 `linux/amd64` Docker 映像。
3. **部署**:
   - 停止並移除現有的 `media-grabber` 容器。
   - 使用新映像啟動容器,並掛載 `logs` 與 `output` 目錄。
4. **驗證**: 執行 `/health` 端點檢查。

## Gitea Runner 配置需求
要在伺服器上運行此流程,您需要安裝並配置 [Gitea Actions Runner](https://docs.gitea.com/usage/actions/quickstart):

1. **安裝 Runner**: 在 Gitea 伺服器或同主機安裝 `act_runner`。
2. **Docker 權限**: Runner 需要能存取宿主機的 Docker socket (例如: `/var/run/docker.sock`)。
3. **標籤配置**: Runner 需具備 `ubuntu-latest` 標籤(或對應您系統的標籤)。

## Secrets 配置
請至 Gitea Repository 設定中的 **Actions -> Secrets** 新增以下變數:

| 變數名稱 | 說明 | 範例值 |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | 前端 API 基礎 URL | `https://media.brianhan.cc` |
| `MG_MAX_TRANSCODE_WORKERS` | (可選) 並發轉碼工作數 | `2` |
| `MG_LOG_LEVEL` | (可選) 日誌級別 | `INFO` |

## 檔案說明
- **工作流程檔案**: `.gitea/workflows/ci-cd.yml`
- **Dockerfile**: `scripts/Dockerfile` (多階段建置)

## 故障排除
1. **建置失敗**: 檢查 Runner 資源(磁碟空間)及 Docker buildx 是否正常。
2. **部署後無法連線**: 檢查宿主機 8080 端口是否被佔用或防火牆限制。
3. **掛載目錄權限**: 確保 `logs` 和 `output` 資料夾對於 Docker 容器有寫入權限。
