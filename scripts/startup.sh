# Set image and container names
IMAGE_NAME="sacahan/media-grabber"
CONTAINER_NAME="media-grabber"

# Check arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
	echo "Usage: ./startup.sh [--force]"
	echo "  --force   Remove local image and pull latest from Docker Hub before starting container."
	echo "  --help    Show this help message."
	exit 0
fi

# Remove local image and pull latest if --force specified
if [[ "$1" == "--force" ]]; then
	echo "Removing local image and pulling latest from Docker Hub..."
	docker image rm -f $IMAGE_NAME || true
	docker pull $IMAGE_NAME
fi

# Stop and remove existing container if it exists
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
	echo "Stopping and removing existing container..."
	docker stop $CONTAINER_NAME
	docker rm $CONTAINER_NAME
fi

# Run the Docker container
echo "Running Docker container..."
docker run -d --restart unless-stopped -p 8080:8080 --name $CONTAINER_NAME $IMAGE_NAME

echo "Application is running on http://localhost:8080"

# Usage:
#   ./startup.sh           # Use local image if exists
#   ./startup.sh --force   # Remove local image and pull latest from Docker Hub
#   ./startup.sh --help    # Show help
