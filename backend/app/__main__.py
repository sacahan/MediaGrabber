"""
MediaGrabber - 應用程式啟動點

支持以下執行方式：
  python -m app.web          # 啟動 Flask Web 伺服器
  python -m app.cli.main     # 執行 CLI 命令
"""

import sys

if __name__ == "__main__":
    # 根據指令決定執行哪個模組
    if len(sys.argv) > 1:
        # 如果有額外參數，假設是 CLI 命令
        from app.cli.main import cli

        cli()
    else:
        # 預設執行 Web 伺服器
        from app.web import create_app

        app = create_app()
        app.run(host="127.0.0.1", port=8080, debug=False)
