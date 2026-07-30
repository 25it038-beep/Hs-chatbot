# HSBot - Start Development Environment
param(
    [switch]$Build,
    [switch]$Prod,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
HSBot Development Script

Usage:
  .\scripts\start.ps1             Start development environment
  .\scripts\start.ps1 -Build      Build Docker images
  .\scripts\start.ps1 -Prod       Start production environment

Commands:
  backend      Start only the backend
  frontend     Start only the frontend
  docker       Start with Docker Compose
"@
    exit
}

function Start-Backend {
    Write-Host "Starting backend..." -ForegroundColor Green
    Set-Location -Path "$PSScriptRoot\..\backend"
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

function Start-Frontend {
    Write-Host "Starting frontend..." -ForegroundColor Green
    Set-Location -Path "$PSScriptRoot\..\frontend"
    npm run dev
}

function Start-Docker {
    if ($Prod) {
        Write-Host "Starting production environment..." -ForegroundColor Green
        docker compose -f "$PSScriptRoot\..\docker-compose.yml" -f "$PSScriptRoot\..\docker-compose.prod.yml" up --build -d
    } elseif ($Build) {
        Write-Host "Building and starting..." -ForegroundColor Green
        docker compose -f "$PSScriptRoot\..\docker-compose.yml" up --build -d
    } else {
        Write-Host "Starting Docker environment..." -ForegroundColor Green
        docker compose -f "$PSScriptRoot\..\docker-compose.yml" up -d
    }
}

# Check command line args
$cmd = $args[0]
switch ($cmd) {
    "backend" { Start-Backend }
    "frontend" { Start-Frontend }
    "docker" { Start-Docker }
    default {
        if ($Build -or $Prod) {
            Start-Docker
        } else {
            Write-Host @"
HSBot Development
=================
Available commands:
  .\scripts\start.ps1 backend      Start backend server
  .\scripts\start.ps1 frontend     Start frontend dev server
  .\scripts\start.ps1 docker       Start with Docker Compose
  .\scripts\start.ps1 -Build       Build and start Docker
  .\scripts\start.ps1 -Prod        Start production stack
"@
        }
    }
}
