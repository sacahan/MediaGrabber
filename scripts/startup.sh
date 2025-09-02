# Set image and container names
IMAGE_NAME="sacahan/media-grabber"
CONTAINER_NAME="media-grabber"

# 獲取專案根目錄的絕對路徑
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Allow overriding the frontend API base URL via first argument or VITE_API_BASE_URL env var
# Usage: ./build_and_run.sh [VITE_API_BASE_URL]
DEFAULT_API_BASE_URL="http://localhost:8080"
VITE_API_BASE_URL_INPUT="${1:-${VITE_API_BASE_URL:-$DEFAULT_API_BASE_URL}}"
echo "Using VITE_API_BASE_URL=${VITE_API_BASE_URL_INPUT} for frontend build"

# Stop and remove existing container if it exists
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# Build the Docker image
echo "Building Docker image..."
docker build --build-arg VITE_API_BASE_URL="$VITE_API_BASE_URL_INPUT" -t $IMAGE_NAME -f "$PROJECT_ROOT/Dockerfile" "$PROJECT_ROOT"

# Run the Docker container
echo "Running Docker container..."
docker run -d --restart unless-stopped -p 8080:8080 --name $CONTAINER_NAME $IMAGE_NAME

echo "Application is running on http://localhost:8080"
