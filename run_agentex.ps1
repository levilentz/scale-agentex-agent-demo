param(
    [switch]$Podman
)

# Set container runtime based on parameter
$ContainerRuntime = if ($Podman) { "podman" } else { "docker" }

if ($Podman) {
    Write-Host "Using Podman instead of Docker"
}

Write-Host "========================================"
Write-Host "Starting $ContainerRuntime build process..."
Write-Host "Using Dockerfile.base to build image 'local-base:latest'"
Write-Host "========================================"

# Run the build command
$buildResult = & $ContainerRuntime build -f Dockerfile.base -t local-base:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ $ContainerRuntime image 'local-base:latest' built successfully."
    Write-Host "========================================"
    Write-Host "Starting $ContainerRuntime Compose process..."
    Write-Host "This will build and start all services defined in docker-compose.yml"
    Write-Host "========================================"

    & $ContainerRuntime compose -f scale-agentex/docker-compose.yaml -f docker-compose.slim.yaml up --build
} else {
    Write-Host "❌ $ContainerRuntime build failed. Compose will not be executed."
    exit 1
}