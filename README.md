# Local Whisper Transcriber for Windows

A **standalone no-browser Windows desktop app** for local audio/video transcription.

You choose an audio/video file, click **Start transcription** or **Start translation**, review the result, then manually save only the files you want:

- transcript text inside the desktop window
- optional `.txt` transcript file
- optional `.srt` subtitle file
- optional `.vtt` subtitle file

It uses `faster-whisper` locally. No paid OpenAI API key is required.

## Privacy

Your audio is processed on your PC.

The first time you use a Whisper model, the model files may download from Hugging Face. After that, the model is cached locally and can be reused.

## Current app type

This version is a true desktop app:

```text
PySide6 desktop window + faster-whisper engine
```

It does **not** run a browser UI and does **not** open `127.0.0.1`.

## Requirements for source/script version

1. Windows 10/11
2. Python 3.11 or 3.12
3. Internet for first install and first model download

Recommended Python:

```text
https://www.python.org/downloads/release/python-3119/
```

Important during Python install:

```text
Check: Add python.exe to PATH
```

Do **not** use Python 3.14 for this project yet. Some local AI/packaging dependencies can lag behind the newest Python releases.

## Install from source

Double-click:

```text
install_windows.bat
```

Wait until install completes.

## Start the desktop app from source

Double-click:

```text
start.bat
```

A normal Windows desktop window should open. No browser should open.

## Build a portable Windows EXE

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

Important: do **not** share only the `.exe`. PyInstaller creates supporting files beside it.

## Debug packaged EXE

If the EXE does not open, run:

```text
run_exe_debug.bat
```

It writes:

```text
exe_debug_log.txt
```

Use that log to troubleshoot packaging errors.

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

For a proper installer, use the free Inno Setup tool.

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

The installer is created in:

```text
installer-output\LocalWhisperTranscriberSetup.exe
```

## Recommended settings

Start with:

```text
Preset: Balanced
Language: choose manually if known, otherwise Auto detect
Task: transcribe
```

For normal use, you do **not** need to change CPU threads or beam size. The preset controls those advanced speed/accuracy settings for you.

### What does Task mean?

```text
transcribe = write the speech in the original spoken language
translate to English = translate spoken audio into English
```

Important: Whisper's built-in `translate` mode translates **to English**. It is not a general Russian-to-Spanish or English-to-Russian translator.

If you need English speech → Russian text, the app needs a second translation step after transcription, using a local translation model such as Argos Translate, NLLB, MarianMT, or another offline translator. That can be added later, but it is separate from Whisper itself.

For example:

```text
Russian audio + transcribe = Russian text
Russian audio + translate  = English text
Spanish audio + translate  = English text
```

Use `transcribe` for normal transcripts.

For faster transcription:

```text
Preset: Fast draft
Language: choose the real language manually
```

For better accuracy:

```text
Preset: High accuracy
Model: medium
```

For maximum accuracy:

```text
Preset: Maximum accuracy / slow
Model: large-v3
```

`large-v3` is most accurate but can be slow/heavy.

## Speed tips

1. Pick the language manually when you know it.
2. Use `Fast draft` for rough transcript.
3. Use `Balanced` for normal daily work.
4. Use `High accuracy` only when quality matters more than time.
5. Keep `Skip silence` enabled to skip long quiet parts.

## Supported files

Usually works with:

```text
mp3
wav
m4a
mp4
mov
webm
mkv
aac
flac
```

If a file format fails, convert it to `.mp3` or `.wav` first.

## Troubleshooting

### Python not found

Install Python 3.11/3.12 and make sure `Add python.exe to PATH` is checked.

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

This is normal. PySide6, Whisper, CTranslate2, and their dependencies are heavy.

### First transcription downloads model

This is normal. The EXE contains the app, not every Whisper model. Models download on first use and are cached locally.

## Roadmap

Possible future improvements:

- batch transcription
- speaker names / diarization
- transcript cleanup
- summaries
- translation workflow
- transcript history
- model manager
