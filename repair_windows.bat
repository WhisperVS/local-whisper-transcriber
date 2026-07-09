@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Local Whisper Transcriber - Repair
echo ========================================
echo.

echo This will remove the current .venv and reinstall dependencies.
echo It will NOT delete your audio files.
echo.
pause

if exist ".venv" (
    echo Removing old virtual environment...
    rmdir /s /q .venv
)

call install_windows.bat
