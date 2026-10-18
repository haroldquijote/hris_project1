@echo off
setlocal

cd /d C:\Users\harold\hris_project1\biometric\kiosk

REM Check if Flask is already running on port 5000
netstat -ano | findstr ":5000" | findstr "LISTENING" > nul
if errorlevel 1 (
    echo [start] Starting kiosk server...
    start "Kiosk Server" cmd /k "python kiosk_app.py"
    echo [start] Waiting 8 seconds for server to boot...
    timeout /t 8 /nobreak > nul
) else (
    echo [start] Server already running on port 5000.
)

echo [start] Opening enrollment page...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" http://localhost:5000/enroll

echo [start] Enrollment page opened.
echo [start] Enter employee ID + finger number, then scan 3 times.

endlocal
exit