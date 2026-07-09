param(
    [string]$ExePath = "$PSScriptRoot\dist\LocalWhisperTranscriber\LocalWhisperTranscriber.exe"
)

Write-Host "Checking EXE path:" $ExePath

if (!(Test-Path $ExePath)) {
    Write-Host "EXE not found: $ExePath" -ForegroundColor Red
    Write-Host "Build the EXE first with build_exe_windows.bat"
    pause
    exit 1
}

$ResolvedExe = (Resolve-Path $ExePath).Path
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Local Whisper Transcriber.lnk"
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ResolvedExe
$Shortcut.WorkingDirectory = Split-Path $ResolvedExe
$Shortcut.Description = "Local private audio/video transcription app"
$Shortcut.Save()

Write-Host "Desktop shortcut created:" -ForegroundColor Green
Write-Host $ShortcutPath
Write-Host "Target:" $ResolvedExe
pause
