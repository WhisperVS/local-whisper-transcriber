@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Local Whisper Transcriber - EXE Debug Run
echo ========================================
echo.

set EXE_PATH=%~dp0dist\LocalWhisperTranscriber\LocalWhisperTranscriber.exe
set LOG_PATH=%~dp0exe_debug_log.txt

if not exist "%EXE_PATH%" (
    echo EXE was not found here:
    echo %EXE_PATH%
    echo.
    echo Build it first by running:
    echo build_exe_windows.bat
    echo.
    pause
    exit /b 1
)

echo Running:
echo %EXE_PATH%
echo.
echo A log will be saved here:
echo %LOG_PATH%
echo.
echo If the app fails, send me a screenshot of this window or the exe_debug_log.txt file.
echo.

"%EXE_PATH%" > "%LOG_PATH%" 2>&1

echo.
echo ========================================
echo App closed or crashed.
echo Exit code: %ERRORLEVEL%
echo ========================================
echo.
echo Last log lines:
echo.
powershell -NoProfile -Command "if (Test-Path '%LOG_PATH%') { Get-Content '%LOG_PATH%' -Tail 80 }"
echo.
pause
