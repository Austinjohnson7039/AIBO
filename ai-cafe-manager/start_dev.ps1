# AIBO Dev Launcher
# Run this script to start all services at once

Write-Host "🚀 Starting AIBO AI Cafe Manager..." -ForegroundColor Yellow

# Start FastAPI backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\Users\user\Desktop\Cloud\AIBO\ai-cafe-manager'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8001" -WindowStyle Normal

Start-Sleep 2

# Start React frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\Users\user\Desktop\Cloud\AIBO\ai-cafe-manager\frontend'; npm run dev" -WindowStyle Normal

Start-Sleep 3

# Open browser
Start-Process "http://localhost:3000"

Write-Host "✅ All services started!" -ForegroundColor Green
Write-Host "   Backend:  http://localhost:8001" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor Cyan
