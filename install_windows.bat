@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Local Whisper Transcriber - Installer
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    echo Install Python 3.11 from https://www.python.org/downloads/release/python-3119/
    echo IMPORTANT: during install, check "Add python.exe to PATH".
    pause
    exit /b 1
)

set PYTHON_CMD=
py -3.11 --version >nul 2>nul
if not errorlevel 1 set PYTHON_CMD=py -3.11

if "%PYTHON_CMD%"=="" (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set PYTHON_CMD=py -3.12
)

if "%PYTHON_CMD%"=="" (
    echo Compatible Python was not found.
    echo.
    echo This app needs Python 3.11 or 3.12.
    echo Python 3.13/3.14 can break Gradio and faster-whisper dependencies.
    echo.
    echo Install Python 3.11 from:
    echo https://www.python.org/downloads/release/python-3119/
    echo.
    echo Then run this installer again.
    pause
    exit /b 1
)

echo Using Python:
%PYTHON_CMD% --version

if exist ".venv" (
    echo Existing .venv found.
) else (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Install failed.
    echo If it complains about Microsoft Visual C++ Build Tools, install:
    echo https://visualstudio.microsoft.com/visual-cpp-build-tools/
    pause
    exit /b 1
)

echo.
echo Install complete.
echo Run start.bat to open the app.
pause
