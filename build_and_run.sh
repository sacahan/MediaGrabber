#!/bin/bash

# Set image and container names
IMAGE_NAME="mediagrabber"
CONTAINER_NAME="mediagrabber-app"

# Stop and remove existing container if it exists
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# Run the Docker container
echo "Running Docker container..."
docker run -d -p 8080:8080 --name $CONTAINER_NAME $IMAGE_NAME

echo "Application is running on http://localhost:8080"
