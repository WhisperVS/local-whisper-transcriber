@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo App is not installed yet.
    echo Run install_windows.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Starting Local Whisper Transcriber desktop app...
python app.py
pause
