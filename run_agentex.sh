#!/bin/bash

# Enable verbose output and exit on error
set -e

echo "========================================"
echo "Starting Docker build process..."
echo "Using Dockerfile.base to build image 'local-base:latest'"
echo "========================================"

# Run the Docker build command
if docker build -f Dockerfile.base -t local-base:latest .; then
    echo "✅ Docker image 'local-base:latest' built successfully."
    echo "========================================"
    echo "Starting Docker Compose process..."
    echo "This will build and start all services defined in docker-compose.yml"
    echo "========================================"

    # Run Docker Compose with build
    #docker compose build
    docker compose -f docker-compose.slim.yaml up --build
else
    echo "❌ Docker build failed. Docker Compose will not be executed."
    exit 1
fi