@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Local Whisper Transcriber - EXE Builder
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    echo Install Python 3.11 from https://www.python.org/downloads/release/python-3119/
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
    echo Compatible Python was not found. Install Python 3.11 or 3.12.
    pause
    exit /b 1
)

echo Using Python:
%PYTHON_CMD% --version

if exist ".buildvenv" (
    echo Using existing build virtual environment.
) else (
    echo Creating build virtual environment...
    %PYTHON_CMD% -m venv .buildvenv
)

call .buildvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building EXE. This can take several minutes...
pyinstaller --noconfirm LocalWhisperTranscriber.spec

if errorlevel 1 (
    echo.
    echo EXE build failed.
    pause
    exit /b 1
)

echo.
echo Build complete.
echo Your portable program is here:
echo dist\LocalWhisperTranscriber\LocalWhisperTranscriber.exe
echo.
echo If PyInstaller created build\LocalWhisperTranscriber\warn-LocalWhisperTranscriber.txt,
echo that file may contain harmless optional-module warnings. If the EXE does not open,
echo run run_exe_debug.bat and send exe_debug_log.txt.
echo.
echo You can copy the whole folder:
echo dist\LocalWhisperTranscriber
echo to another Windows PC and run the EXE.
echo.
pause
