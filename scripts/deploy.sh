#!/bin/zsh

# 確保腳本在錯誤時停止執行
set -e

# 檢查 Docker 是否安裝
if ! command -v docker &> /dev/null
then
    echo "Docker 未安裝，請先安裝 Docker。"
    exit 1
fi

# 獲取專案根目錄的絕對路徑
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# 預設要支援的平台
# PLATFORMS="linux/amd64,linux/arm64"
PLATFORMS="linux/amd64"

# 若要推到 Docker Hub，預設的使用者帳號
DOCKERHUB_USER="sacahan"
IMAGE_NAME="media-grabber"
DOCKERFILE_PATH="$PROJECT_ROOT/Dockerfile"

# 預設的 API 基礎 URL
DEFAULT_API_BASE_URL="https://media.brianhan.cc"
VITE_API_BASE_URL_INPUT="${1:-${VITE_API_BASE_URL:-$DEFAULT_API_BASE_URL}}"
echo "Using VITE_API_BASE_URL=${VITE_API_BASE_URL_INPUT} for frontend build"

# 建置多平台映像並推送到 Docker Hub（不保留本地 image）
BUILDER_NAME="multiarch-builder"

if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
    echo "建立 buildx builder: $BUILDER_NAME"
    docker buildx create --name "$BUILDER_NAME" --driver docker-container --use
else
    echo "使用已存在的 buildx builder: $BUILDER_NAME"
    docker buildx use "$BUILDER_NAME"
fi

docker buildx inspect --bootstrap
echo "註冊 QEMU multiarch binfmt 支援 (需要 Docker 允許 --privileged) ..."
docker run --rm --privileged tonistiigi/binfmt:latest --install all || \
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes || true

IMAGE_TAG="${DOCKERHUB_USER}/${IMAGE_NAME}:latest"
echo "建置並推送多平台映像: image=$IMAGE_TAG, dockerfile=$DOCKERFILE_PATH"
# buildx --push 只推送，不保留本地 image
docker buildx build --platform "$PLATFORMS" --push -t "$IMAGE_TAG" --build-arg VITE_API_BASE_URL="$VITE_API_BASE_URL_INPUT" -f "$DOCKERFILE_PATH" "$PROJECT_ROOT"

echo "$IMAGE_TAG 推送完成！"
