# Changelog

## Unreleased

### Changed

- Replaced the previous Gradio/browser UI with a true PySide6 desktop application.
- The app now opens as a normal Windows desktop window instead of a `127.0.0.1` browser page.
- Updated dependencies to `PySide6` + `faster-whisper`.
- Updated PyInstaller packaging for desktop EXE builds.
- Rewrote README for the standalone no-browser workflow.

### Kept

- Local faster-whisper transcription.
- TXT, SRT, and VTT export.
- Windows install, start, repair, EXE build, shortcut, and installer scripts.
- Speed/accuracy presets.

## Initial baseline

### Added

- Local transcription application.
- Windows install, start, and repair scripts.
- Windows PyInstaller EXE builder.
- Optional Inno Setup installer script.
- Desktop shortcut helper.
- Debug launcher for packaged EXE troubleshooting.
