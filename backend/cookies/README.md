# Cookies 目錄

此目錄存儲各個平台的認證 cookies。

## 安全性說明

⚠️ **重要**：此目錄包含敏感的認證信息，請勿：

- 將任何 cookies 文件提交到版本控制系統
- 分享給他人
- 在公共環境中暴露

## 支持的 Platform

- `instagram.txt` - Instagram 登入 cookies
- `threads.txt` - Threads 登入 cookies（與 Instagram 共用認證系統）
- 未來可添加：facebook.txt, twitter.txt 等

## Threads 特別說明

Threads 與 Instagram 同屬 Meta 平台，共用認證系統。你可以：

1. **使用 Instagram cookies** - 將 `instagram.txt` 放在此目錄，系統會自動使用
2. **使用 Threads cookies** - 從 threads.net 導出並存為 `threads.txt`
3. **透過 Web UI** - 在 Threads 分頁中直接貼上 cookies 內容

優先順序：用戶提供的 cookies > threads.txt > instagram.txt

## 格式

使用標準的 Netscape HTTP Cookie File 格式。

範例格式：

```text
# Netscape HTTP Cookie File
.threads.net    TRUE    /    TRUE    0    sessionid    xxxxx
.instagram.com    TRUE    /    TRUE    0    sessionid    xxxxx
```

## 取得 Cookies 步驟

1. 安裝瀏覽器擴展（如 "Get cookies.txt LOCALLY"）
2. 登入 [threads.net](https://www.threads.net) 或 [instagram.com](https://www.instagram.com)
3. 點擊擴展圖示，選擇「Export」匯出 cookies
4. 將檔案保存到此目錄

```bash
chmod 644 backend/cookies/*.txt
```

## 在應用中使用

### CLI 使用

```bash
# 使用預設 cookies (threads.txt 或 instagram.txt)
mediagrabber download --url "https://www.threads.net/@user/post/..." --format mp4

# 指定 cookies 檔案
mediagrabber download --url "https://www.threads.net/@user/post/..." --cookies my_cookies.txt
```

### Web UI 使用

在 Threads 分頁中，將匯出的 cookies 內容貼到「Cookies」輸入框中。

### Web API 使用

將 cookies 內容以 Base64 編碼後傳遞給 API 端點：

```json
{
  "url": "https://www.threads.net/@user/post/...",
  "format": "mp4",
  "cookiesBase64": "IyBOZXRzY2FwZSBIVFRQIENvb2tpZSBGaWxl..."
}
```
