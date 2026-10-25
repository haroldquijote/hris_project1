' ──────────────────────────────────────────────────────────────────────
' Kiosk Launcher
' Double-click this file to launch the biometric kiosk:
'   - Starts Flask hidden (no terminal window)
'   - Waits for the server to boot
'   - Opens Chrome fullscreen in kiosk mode
' ──────────────────────────────────────────────────────────────────────

Set WshShell = CreateObject("WScript.Shell")

' Move into the kiosk folder so relative paths work
WshShell.CurrentDirectory = "C:\Users\harold\hris_project1\biometric\kiosk"

' ── Check if Flask is already running on port 5000 ──────────────────
Dim portInUse
portInUse = False
On Error Resume Next
Dim exec
Set exec = WshShell.Exec("cmd /c netstat -an | findstr :5000 | findstr LISTENING")
If Not exec Is Nothing Then
    If InStr(exec.StdOut.ReadAll(), "LISTENING") > 0 Then portInUse = True
End If
On Error GoTo 0

' ── Start Flask hidden if not already running ───────────────────────
If Not portInUse Then
    ' 0 = hidden window, False = don't wait for it to finish
    WshShell.Run "cmd /c python kiosk_app.py >> kiosk.log 2>&1", 0, False
    ' Give Flask ~8 seconds to boot and load fingerprints from server
    WScript.Sleep 8000
End If

' ── Launch Chrome in fullscreen app mode ────────────────────────────
WshShell.Run """C:\Program Files\Google\Chrome\Application\chrome.exe"" " & _
    "--app=http://localhost:5000 " & _
    "--start-fullscreen " & _
    "--noerrdialogs " & _
    "--disable-infobars " & _
    "--disable-session-crashed-bubble", 1, False