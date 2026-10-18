@echo off
cd /d C:\Users\harold\hris_project1\biometric\kiosk

REM Start Flask server in its own window
start "Kiosk Server" cmd /k "python kiosk_app.py"

REM Wait for the server to boot up
timeout /t 8 /nobreak

REM Open Chrome as app (no browser chrome)
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:5000 --start-fullscreen --noerrdialogs --disable-infobars --disable-session-crashed-bubble

exit