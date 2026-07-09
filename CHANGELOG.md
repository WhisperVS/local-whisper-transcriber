# Changelog

## Unreleased

### Changed

- Fixed packaged EXE startup reliability: the app now lazy-loads faster-whisper only when transcription starts, pins Windows build dependencies, disables UPX, and creates a console debug EXE for crash logs.
- Reduced fullscreen dead space by widening the main content cap and letting Settings fields fill their columns instead of staying narrow on large monitors.
- Made the app layout adaptive for arbitrary window resizing: smaller widths switch Settings to a single-column layout instead of relying on one fixed resolution.
- Reworked the settings area to use explicit card titles and label-above-field controls so combo boxes do not visually stack on top of each other on Windows.
- Polished the desktop UI for fullscreen and smaller windows: cleaner dark theme, centered max-width content, stronger visual hierarchy, bigger touch targets, clearer step titles, and better spacing around the save buttons.
- Slimmed the PyInstaller spec so the EXE builder no longer intentionally collects all PySide6 and NumPy test/optional modules. This should reduce noisy warnings and package size.
- Added an in-app model explanation under the `Model` setting so beginners can see what `tiny`, `base`, `small`, `medium`, and `large-v3` mean without opening documentation.
- Fixed smaller-window layout so manual save buttons stay below the transcript field instead of overlapping it.
- Moved manual save buttons under the transcript field to declutter the Run section.
- Renamed the translation task to `translate to English` so Whisper's built-in limitation is clear.
- Manual save workflow: results stay in the app until the user clicks `Save TXT`, `Save SRT`, or `Save VTT`.
- The main action button now changes between `Start transcription` and `Start translation` based on the selected task.
- Removed automatic transcript/subtitle file creation after every run.
- Simplified the desktop UI by removing CPU threads, beam size, and compute type from the main workflow.
- Presets now keep advanced speed/accuracy settings behind the scenes for beginner-friendly use.
- Added worker/thread cleanup so multiple files can be transcribed in one app session.
- Documented `transcribe` vs `translate` behavior.

### Previous changes

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
