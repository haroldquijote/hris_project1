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

echo [start] Opening attendance kiosk (full screen)...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:5000/ --start-fullscreen --noerrdialogs --disable-infobars --disable-session-crashed-bubble

echo [start] Attendance kiosk launched.
echo [start] To exit: press Alt+F4 in the kiosk window.
echo [start] Server window stays open until you close it.

endlocal
exit