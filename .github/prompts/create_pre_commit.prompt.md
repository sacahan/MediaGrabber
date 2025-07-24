---
mode:  agent
description: 'Create a pre-commit hook to enforce code quality standards before committing changes.'
---

# 建立 Pre-commit Hook 步驟如下：

## 1. 使用 uv 安裝 pre-commit

- 檢查是否已安裝 uv

```zsh
if ! uv --version &> /dev/null; then
	echo "uv 未安裝，請先安裝 uv。"
	# 安裝 uv 工具（若尚未安裝）
	# macOS and Linux
	curl -LsSf https://astral.sh/uv/install.sh | sh

	# Windows
	# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
fi
```

- 使用 uv 安裝 pre-commit

```zsh
uv add pre-commit
```

- (可選) 將 pre-commit 加入專案的 uv.json

```zsh
uv link pre-commit
```

## 2. 在 ${workspaceFolderBasename} 根目錄新增 .pre-commit-config.yaml，並增加以下內容：

```yaml
# .pre-commit-config.yaml 範例
repos:
  # 使用 pre-commit 官方提供的常用 hook 工具集
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0 # 使用的版本
    hooks:
      - id: trailing-whitespace # 移除每行結尾多餘的空白
      - id: end-of-file-fixer # 確保檔案結尾有一個換行符號
      - id: check-yaml # 驗證 YAML 格式是否正確
      - id: check-added-large-files # 阻止加入超過預設大小的新檔案
	  	args: ["--maxkb=5000"] # 調整為 5000KB
      - id: check-merge-conflict # 檢查是否有合併衝突的標記
```

## 3. (可選) 依據程式語言增加額外的 hook

```yaml
repos:
  # Python
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
        - id: check-docstring-first
        name: "Check Python docstrings"
        args: ["--strict"]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.5
    hooks:
      - id: ruff-format # 格式化 Python 檔案（類似 black）
      - id: ruff # 使用 Ruff 檢查 Python 程式碼品質（如 flake8）

  # Java
  - repo: https://github.com/detekt/detekt
    rev: v1.22.0
    hooks:
      - id: detekt # 檢查 Java 程式碼品質

  # JavaScript / TypeScript
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.45.0
    hooks:
      - id: eslint # 檢查 JavaScript/TypeScript 程式碼品質
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier # 格式化前端檔案

  # C#
  - repo: https://github.com/josefpihrt/pre-commit-hooks
    rev: v1.0.0
    hooks:
      - id: dotnet-format # 格式化 C# 檔案
      - id: dotnet-analyzers # 使用 .NET 分析器檢查 C# 程式碼品質
```

## 4. 安裝 Git hook 到專案 .git/hooks

```zsh
pre-commit install
```

## 5. 手動測試所有檔案

```zsh
pre-commit run --all-files
```

## 6. 檢查目前 hook 狀態

```zsh
uv exec pre-commit status
```

Let's do it step by step!
