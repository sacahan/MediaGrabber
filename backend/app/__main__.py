"""
MediaGrabber - 應用程式啟動點

此檔案是當使用 `python -m app` 執行時的入口點。
根據命令列參數自動決定啟動 Web 服務或 CLI 模式。

支持的執行方式：
  python -m app              # 預設啟動 Web 服務
  python -m app download ... # CLI 模式：執行下載命令
  python -m app.web          # 直接啟動 Web 服務
  python -m app.cli.main     # 直接執行 CLI
"""

import sys

if __name__ == "__main__":
    # 根據命令列參數決定執行模式
    if len(sys.argv) > 1:
        # 如果有額外參數，進入 CLI 模式
        # 例如：python -m app download --url ...
        from app.cli.main import cli

        cli()  # 執行 CLI 命令解析器
    else:
        # 沒有參數時，預設啟動 Web 服務
        from app.web import create_app

        app = create_app()
        # 監聽在 127.0.0.1:8080
        app.run(host="127.0.0.1", port=8080, debug=False)
