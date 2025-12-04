#!/usr/bin/env python3
"""
MediaGrabber Web Service - Flask REST API Server

新統一的 Flask 應用入點，整合：
- 新的 REST API 端點 (/api/downloads/*)
- Swagger/OpenAPI 文檔 (/api/docs)
- Svelte 前端靜態資源服務
- 進度查詢和下載管理
"""

import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger

# 導入新的 API 藍圖
from app.api.downloads import downloads_bp

# Swagger 配置
SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
}

SWAGGER_TEMPLATE = {
    "info": {
        "title": "MediaGrabber API",
        "description": "媒體下載服務 API - 支援 YouTube、Instagram、Facebook、X (Twitter) 等平台",
        "version": "1.0.0",
        "contact": {
            "name": "MediaGrabber",
            "url": "https://github.com/sacahan/MediaGrabber",
        },
    },
    "basePath": "/api",
    "schemes": ["http", "https"],
    "tags": [
        {"name": "downloads", "description": "下載任務管理"},
        {"name": "system", "description": "系統資訊"},
    ],
}


def create_app():
    """建立並配置 Flask 應用程式"""

    # 靜態資源路徑 - 支援開發環境和 Docker 容器
    if Path("/app/frontend/dist").exists():
        # Docker 容器環境
        frontend_dist = Path("/app/frontend/dist")
    else:
        # 開發環境
        frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

    app = Flask(__name__, static_folder=str(frontend_dist), static_url_path="/")

    # 啟用 CORS
    CORS(app)

    # 設定日誌
    _setup_logging(app)

    # 初始化 Swagger
    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)

    # 註冊 API 藍圖
    app.register_blueprint(downloads_bp, url_prefix="/api/downloads")

    # API 根端點 - 概覽
    @app.route("/api", methods=["GET"])
    @app.route("/api/", methods=["GET"])
    def api_overview():
        """
        API 概覽
        ---
        tags:
          - system
        responses:
          200:
            description: API 資訊與可用端點清單
        """
        return jsonify(
            {
                "name": "MediaGrabber API",
                "version": "1.0.0",
                "description": "媒體下載服務 API - 支援 YouTube、Instagram、Facebook、X (Twitter)",
                "documentation": "/api/docs",
                "health": "/health",
                "endpoints": {
                    "downloads": {
                        "POST /api/downloads": "提交新的下載任務",
                        "GET /api/downloads/<job_id>": "取得任務狀態與結果",
                        "GET /api/downloads/<job_id>/progress": "取得任務即時進度",
                    },
                },
                "supportedPlatforms": [
                    "youtube.com",
                    "youtu.be",
                    "instagram.com",
                    "facebook.com",
                    "x.com",
                    "twitter.com",
                ],
                "supportedFormats": ["mp4", "mp3"],
            }
        ), 200

    # 前端路由（SPA fallback）
    @app.route("/")
    @app.route("/<path:path>")
    def serve_frontend(path="index.html"):
        """服務 Svelte 前端應用"""
        if path.startswith("api") or path.startswith("flasgger_static"):
            return {"error": "Not found"}, 404
        if path != "index.html" and (frontend_dist / path).exists():
            return app.send_static_file(path)
        return app.send_static_file("index.html")

    # 健康檢查端點
    @app.route("/health", methods=["GET"])
    def health_check():
        """
        健康檢查
        ---
        tags:
          - system
        responses:
          200:
            description: 服務健康狀態
        """
        return {"status": "ok", "service": "MediaGrabber"}, 200

    return app


def _setup_logging(app):
    """配置應用日誌（從環境變數讀取設定）"""
    import logging
    from logging.handlers import RotatingFileHandler

    # 從環境變數讀取日誌設定
    log_dir = os.getenv("MG_LOG_DIR", str(Path(__file__).parent.parent / "logs"))
    log_level = os.getenv("MG_LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("MG_LOG_FORMAT", "text")
    log_max_bytes = int(os.getenv("MG_LOG_MAX_BYTES", "10485760"))  # 10MB
    log_backup_count = int(os.getenv("MG_LOG_BACKUP_COUNT", "5"))

    # 確保日誌目錄存在
    logs_dir = Path(log_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 設定日誌格式
    if log_format == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"name": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # 文件日誌處理器
    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))

    # Console handler for stdout
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))

    # 配置 root logger 以捕獲所有模塊的日誌
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 配置 Flask app logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 記錄日誌配置
    app.logger.info(
        f"日誌配置完成: 目錄={logs_dir}, 級別={log_level}, 格式={log_format}"
    )


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
