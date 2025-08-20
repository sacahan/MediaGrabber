#!/bin/bash

# Simple help output
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        cat <<'USAGE'
Usage: ./build_and_run.sh [VITE_API_BASE_URL]

Positional arguments:
    VITE_API_BASE_URL   Optional. The frontend API base URL to embed at build time.
                                            If omitted, the script checks the environment variable
                                            VITE_API_BASE_URL, otherwise defaults to http://localhost:8080

Environment variables:
    VITE_API_BASE_URL   Same as the positional argument; can be used instead.

Examples:
    # build and run with default (http://localhost:8080)
    ./build_and_run.sh

    # pass custom API base URL
    ./build_and_run.sh https://api.example.com

    # or via environment variable
    VITE_API_BASE_URL=https://api.example.com ./build_and_run.sh
USAGE
        exit 0
fi

# Set image and container names
IMAGE_NAME="mediagrabber"
CONTAINER_NAME="mediagrabber-app"

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
docker build --build-arg VITE_API_BASE_URL="$VITE_API_BASE_URL_INPUT" -t $IMAGE_NAME .

# Run the Docker container
echo "Running Docker container..."
docker run -d -p 8080:8080 --name $CONTAINER_NAME $IMAGE_NAME

echo "Application is running on http://localhost:8080"
