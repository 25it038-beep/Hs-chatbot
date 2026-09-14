# Build and Push HSBot Docker Image to Docker Hub
# Usage: .\build-and-push.ps1 -DockerUsername "your_username"

param(
    [Parameter(Mandatory=$true)]
    [string]$DockerUsername,
    
    [string]$ImageTag = "latest"
)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "HSBot Docker Build & Push" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$ImageName = "$DockerUsername/hsbot-backend:$ImageTag"

Write-Host "Building image: $ImageName" -ForegroundColor Yellow
Write-Host ""

# Check if Docker is running
try {
    docker version >$null 2>&1
} catch {
    Write-Host "ERROR: Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again" -ForegroundColor Red
    exit 1
}

# Build image
Write-Host "[1/3] Building Docker image..." -ForegroundColor Cyan
docker build -t $ImageName -f backend/Dockerfile backend

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Build successful!" -ForegroundColor Green
Write-Host ""

# Login
Write-Host "[2/3] Logging into Docker Hub..." -ForegroundColor Cyan
docker login

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Login failed!" -ForegroundColor Red
    exit 1
}

Write-Host "[2/3] Logged in!" -ForegroundColor Green
Write-Host ""

# Push image
Write-Host "[3/3] Pushing to Docker Hub..." -ForegroundColor Cyan
Write-Host "This may take several minutes..." -ForegroundColor Gray
docker push $ImageName

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Push failed!" -ForegroundColor Red
    exit 1
}

Write-Host "[3/3] Push successful!" -ForegroundColor Green
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "SUCCESS!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your image is now on Docker Hub:" -ForegroundColor Yellow
Write-Host "  $ImageName" -ForegroundColor White
Write-Host ""
Write-Host "Next step: Update Render to use this image" -ForegroundColor Cyan
Write-Host "1. Go to: https://dashboard.render.com/services" -ForegroundColor White
Write-Host "2. Click: hs-chatbot-2" -ForegroundColor White
Write-Host "3. Settings tab → Docker → Image URL" -ForegroundColor White
Write-Host "4. Enter: $ImageName" -ForegroundColor White
Write-Host "5. Save and deploy" -ForegroundColor White
