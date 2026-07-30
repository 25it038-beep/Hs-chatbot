# HSBot Setup Script

Write-Host "=== HSBot Setup ===" -ForegroundColor Cyan

# 1. Set up Python backend
Write-Host "`n[1/4] Setting up Python backend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\..\backend"
if (Test-Path -Path ".venv") {
    Write-Host "  Virtual environment already exists." -ForegroundColor Gray
} else {
    python -m venv .venv
    Write-Host "  Created virtual environment." -ForegroundColor Green
}
& ".venv\Scripts\pip" install -r requirements.txt
Write-Host "  Backend dependencies installed." -ForegroundColor Green

# 2. Set up .env
Write-Host "`n[2/4] Configuring environment..." -ForegroundColor Yellow
if (-not (Test-Path -Path "$PSScriptRoot\..\.env")) {
    Copy-Item -Path "$PSScriptRoot\..\.env.example" -Destination "$PSScriptRoot\..\.env"
    Write-Host "  Created .env from .env.example." -ForegroundColor Green
    Write-Host "  WARNING: Edit .env with your API keys!" -ForegroundColor Red
} else {
    Write-Host "  .env already exists." -ForegroundColor Gray
}

# 3. Set up Node.js frontend
Write-Host "`n[3/4] Setting up frontend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\..\frontend"
npm install
Write-Host "  Frontend dependencies installed." -ForegroundColor Green

# 4. Initialize the database
Write-Host "`n[4/4] Initializing database..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\..\backend"
& ".venv\Scripts\python" -c "
import asyncio
from app.database import init_db
asyncio.run(init_db())
print('  Database initialized.')
"
Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "`nNext steps:"
Write-Host "  1. Edit .env with your API keys"
Write-Host "  2. Run backend:  .\scripts\start.ps1 backend"
Write-Host "  3. Run frontend: .\scripts\start.ps1 frontend"
Write-Host "  4. Open http://localhost:5173"
