# Local Whisper Transcriber for Windows

A simple local transcription program for Windows.

You upload an audio/video file, click **Transcribe**, and get:

- transcript text
- `.txt` download
- `.srt` subtitles
- `.vtt` subtitles

It uses `faster-whisper` locally. No paid OpenAI API key is required.

## Privacy

Your audio is processed on your PC. The first time you choose a Whisper model, it downloads that model from the internet. After that, transcription runs locally.

## Requirements for normal script version

1. Windows 10/11
2. Python 3.11 or 3.12
3. Internet for first install and first model download

Do **not** use Python 3.14 for this app. Some Gradio/faster-whisper dependencies are not stable with Python 3.14 yet.

Recommended install:

```text
https://www.python.org/downloads/release/python-3119/
```

Important during Python install:

```text
Check: Add python.exe to PATH
```

## Install script version

Double-click:

```text
install_windows.bat
```

Wait until it says install complete.

## Start script version

Double-click:

```text
start.bat
```

Browser should open automatically.

If it does not, open:

```text
http://127.0.0.1:7860
```

## Build a portable Windows EXE

If you want to share the app with another Windows PC, build the EXE on Windows.

Double-click:

```text
build_exe_windows.bat
```

It creates:

```text
dist\LocalWhisperTranscriber\LocalWhisperTranscriber.exe
```

Share the whole folder:

```text
dist\LocalWhisperTranscriber
```

Important: do **not** share only the `.exe` from inside that folder. PyInstaller creates supporting files beside it. Share the whole folder, or build the installer below.

## Create a desktop shortcut

After building the EXE, double-click:

```text
create_desktop_shortcut.bat
```

It creates:

```text
Desktop\Local Whisper Transcriber.lnk
```

## Build a real Setup.exe installer

For a proper installer that creates Start Menu/Desktop shortcuts, use the free Inno Setup tool.

Install Inno Setup:

```powershell
winget install JRSoftware.InnoSetup
```

Then:

1. Run `build_exe_windows.bat` first.
2. Open `installer_inno_setup.iss` in Inno Setup.
3. Click **Build**.

Or from PowerShell/CMD if `iscc` is in PATH:

```powershell
iscc installer_inno_setup.iss
```

The installer will be created in:

```text
installer-output\LocalWhisperTranscriberSetup.exe
```

That is the file you can share more easily.

## Recommended settings

Start with the built-in preset:

```text
Speed / accuracy preset: Balanced
Language: Auto detect, or choose English/Russian/Spanish manually
Task: transcribe
```

For faster transcription:

```text
Preset: Fast draft
Language: choose the real language manually instead of Auto detect
Compute type: int8
Beam size: 1
```

For better accuracy:

```text
Preset: High accuracy
Model: medium
Beam size: 5
```

For maximum accuracy:

```text
Preset: Maximum accuracy / slow
Model: large-v3
```

`large-v3` is most accurate but can be slow/heavy.

## Theme options

The app includes switchable themes:

```text
Midnight
Frost
Solar
Clean Light
```

You can change the theme from the top of the app window.

## Speed tips

1. Pick the language manually when you know it. Auto-detect is convenient but slower.
2. Use `Fast draft` for rough transcript.
3. Use `Balanced` for normal daily work.
4. Use `High accuracy` only when quality matters more than time.
5. Keep `Voice activity filter` enabled to skip silence.
6. On CPU-only laptops, `int8` is usually faster than `float32`.

## Supported files

Usually works with:

```text
mp3
wav
m4a
mp4
mov
webm
```

If a file format fails, convert it to `.mp3` or `.wav` first.

## Troubleshooting

### Python not found

Install Python 3.11+ and make sure `Add python.exe to PATH` is checked.

### Install fails with build tools error

Install Microsoft C++ Build Tools:

```text
https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

Usually this is not needed, but some Windows setups require it.

### App opens but transcription is slow

Use:

```text
Fast draft
```

or a smaller model:

```text
tiny or base
```

### Better accuracy

Use:

```text
small or medium
```

Also choose the real language manually instead of Auto detect.

### EXE is very large

This is normal. Whisper, Gradio, CTranslate2, and their dependencies are heavy.

### First transcription downloads model

This is normal. The EXE contains the app, not every Whisper model. Models download on first use and are cached by Hugging Face.

## Notes

Later we can add:

- batch transcription
- speaker names
- cleanup/grammar correction
- summary
- translation
- transcript history
