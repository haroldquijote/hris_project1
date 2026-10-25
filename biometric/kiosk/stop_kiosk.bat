@echo off
echo Stopping kiosk server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo Kiosk server stopped.
timeout /t 2 /nobreak >nul