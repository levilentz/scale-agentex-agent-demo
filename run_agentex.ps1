Write-Host "========================================"
Write-Host "Starting Docker build process..."
Write-Host "Using Dockerfile.base to build image 'local-base:latest'"
Write-Host "========================================"

# Run the Docker build command
$buildResult = docker build -f Dockerfile.base -t local-base:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image 'local-base:latest' built successfully."
    Write-Host "========================================"
    Write-Host "Starting Docker Compose process..."
    Write-Host "This will build and start all services defined in docker-compose.yml"
    Write-Host "========================================"

    docker compose -f scale-agentex/docker-compose.yaml -f docker-compose.slim.yaml up --build
} else {
    Write-Host "❌ Docker build failed. Docker Compose will not be executed."
    exit 1
}