#!/bin/bash

# Enable verbose output and exit on error
set -e

# Parse command line arguments
CONTAINER_RUNTIME="docker"
if [[ "$1" == "--podman" ]]; then
    CONTAINER_RUNTIME="podman"
    echo "Using Podman instead of Docker"
fi

echo "========================================"
echo "Starting ${CONTAINER_RUNTIME} build process..."
echo "Using Dockerfile.base to build image 'local-base:latest'"
echo "========================================"

# Run the build command
if ${CONTAINER_RUNTIME} build -f Dockerfile.base -t local-base:latest .; then
    echo "✅ ${CONTAINER_RUNTIME} image 'local-base:latest' built successfully."
    echo "========================================"
    echo "Starting ${CONTAINER_RUNTIME} Compose process..."
    echo "This will build and start all services defined in docker-compose.yml"
    echo "========================================"

    # Run Compose with build
    #${CONTAINER_RUNTIME} compose build
    ${CONTAINER_RUNTIME} compose --env-file .env -f scale-agentex/docker-compose.yaml -f docker-compose.slim.yaml up --build
else
    echo "❌ ${CONTAINER_RUNTIME} build failed. Compose will not be executed."
    exit 1
fi
