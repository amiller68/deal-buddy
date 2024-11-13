#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Variables
DOCKER_USERNAME="amiller68"
IMAGE_NAME="deal-buddy"
TAG="latest"

# Full image name
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$TAG"

# Build the Docker image
echo "Building Docker image: $FULL_IMAGE_NAME"
docker build -t $FULL_IMAGE_NAME:$TAG .

# Build the worker image
echo "Building worker Docker image: $FULL_IMAGE_NAME-worker"
docker build -t $FULL_IMAGE_NAME:$TAG-worker -f Dockerfile.worker .

# Push the image to Docker Hub
echo "Pushing image to Docker Hub: $FULL_IMAGE_NAME"
docker push $FULL_IMAGE_NAME
docker push $FULL_IMAGE_NAME-worker
docker push $FULL_IMAGE_NAME:$TAG-worker

echo "Image successfully built and pushed to Docker Hub"