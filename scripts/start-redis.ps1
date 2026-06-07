param(
    [string]$ContainerName = "flood-redis",
    [int]$Port = 6379
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker CLI not found. Install Docker Desktop, or run Redis locally another way."
}

docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon is not running. Start Docker Desktop and retry."
}

$existing = docker ps -a --filter "name=^/$ContainerName$" --format "{{.Names}}"
if ($existing -eq $ContainerName) {
    docker start $ContainerName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start existing Redis container '$ContainerName'."
    }
    Write-Host "Redis container '$ContainerName' started."
} else {
    docker run -d `
        --name $ContainerName `
        -p "${Port}:6379" `
        redis:7-alpine `
        redis-server --appendonly yes --save 60 1000 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create/start Redis container '$ContainerName'."
    }
    Write-Host "Redis container '$ContainerName' created and started on port $Port."
}

Write-Host "Health check:"
$ping = docker exec $ContainerName redis-cli ping
if ($LASTEXITCODE -ne 0 -or $ping -notmatch "PONG") {
    Write-Error "Redis health check failed for container '$ContainerName'."
}

Write-Host $ping
