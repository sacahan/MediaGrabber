#!/usr/bin/env python3
"""
MediaGrabber Web Service - Flask REST API Server

新統一的 Flask 應用入點，整合：
- 新的 REST API 端點 (/api/downloads/*)
- Svelte 前端靜態資源服務
- 進度查詢和下載管理
"""

import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS

# 導入新的 API 藍圖
from app.api.downloads import downloads_bp


def create_app():
    """建立並配置 Flask 應用程式"""

    # 靜態資源路徑
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

    app = Flask(__name__, static_folder=str(frontend_dist), static_url_path="/")

    # 啟用 CORS
    CORS(app)

    # 設定日誌
    _setup_logging(app)

    # 註冊 API 藍圖
    app.register_blueprint(downloads_bp, url_prefix="/api")

    # 前端路由（SPA fallback）
    @app.route("/")
    @app.route("/<path:path>")
    def serve_frontend(path="index.html"):
        """服務 Svelte 前端應用"""
        if path != "index.html" and (frontend_dist / path).exists():
            return app.send_static_file(path)
        return app.send_static_file("index.html")

    # 健康檢查端點
    @app.route("/health", methods=["GET"])
    def health_check():
        return {"status": "ok", "service": "MediaGrabber"}, 200

    return app


def _setup_logging(app):
    """配置應用日誌"""
    import logging
    from logging.handlers import RotatingFileHandler

    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # 文件日誌處理器
    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)


if __name__ == "__main__":
    app = create_app()

    # 從環境變數讀取設定
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "8080"))
    debug = os.getenv("FLASK_ENV") == "development"

    print(f"🚀 MediaGrabber Web Service 啟動於 http://{host}:{port}")
    print(f"📊 前端：http://{host}:{port}")
    print(f"🔌 API：http://{host}:{port}/api")

    app.run(host=host, port=port, debug=debug)
