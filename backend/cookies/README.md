# Cookies 目錄

此目錄存儲各個平台的認證 cookies。

## 安全性說明

⚠️ **重要**：此目錄包含敏感的認證信息，請勿：

- 將任何 cookies 文件提交到版本控制系統
- 分享給他人
- 在公共環境中暴露

## 支持的 Platform

- `instagram.txt` - Instagram 登入 cookies
- 未來可添加：facebook.txt, twitter.txt 等

## 格式

使用標準的 Netscape HTTP Cookie File 格式。

## 更新 Cookies

1. 在瀏覽器中登入相應平台
2. 使用瀏覽器擴展（如 "Get cookies.txt"）導出 cookies
3. 轉換為 Netscape 格式並保存到此目錄
4. 確保權限設置為 644（不公開可讀寫）

```bash
chmod 644 backend/cookies/*.txt
```

## 在應用中使用

### CLI 使用

```bash
python backend/media_grabber.py \
  --cookie backend/cookies/instagram.txt \
  --format mp4 \
  "https://www.instagram.com/p/YOUR_POST_ID/"
```

### Web API 使用

將 cookies 文件路徑或 JSON 內容傳遞給 API 端點。
