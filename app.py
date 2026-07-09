"""Local Whisper Transcriber desktop app.

A true no-browser Windows desktop interface built with PySide6 and faster-whisper.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel
from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Local Whisper Transcriber"
APP_VERSION = "1.0.0"

LANGUAGES = {
    "Auto detect": None,
    "English": "en",
    "Russian": "ru",
    "Spanish": "es",
    "Ukrainian": "uk",
    "French": "fr",
    "German": "de",
    "Polish": "pl",
}

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
COMPUTE_TYPES = ["int8", "float32"]
PRESETS = {
    "Fast draft": {"model": "base", "beam": 1, "vad": True, "compute": "int8"},
    "Balanced": {"model": "small", "beam": 3, "vad": True, "compute": "int8"},
    "High accuracy": {"model": "medium", "beam": 5, "vad": True, "compute": "int8"},
    "Maximum accuracy / slow": {"model": "large-v3", "beam": 5, "vad": True, "compute": "int8"},
}
MODEL_CACHE: dict[tuple[str, str, int], WhisperModel] = {}


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0b1020;
    color: #e5e7eb;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10.5pt;
}
QGroupBox {
    border: 1px solid #334155;
    border-radius: 12px;
    margin-top: 12px;
    padding: 14px;
    background-color: #111827;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #93c5fd;
    font-weight: 600;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #020617;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px;
    color: #e5e7eb;
}
QPlainTextEdit { font-family: Consolas, Cascadia Mono, monospace; }
QPushButton {
    background-color: #2563eb;
    border: 0;
    border-radius: 9px;
    color: white;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover { background-color: #1d4ed8; }
QPushButton:disabled { background-color: #475569; color: #cbd5e1; }
QPushButton#secondary { background-color: #334155; }
QPushButton#secondary:hover { background-color: #475569; }
QPushButton#danger { background-color: #dc2626; }
QProgressBar {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #020617;
    text-align: center;
    color: #e5e7eb;
}
QProgressBar::chunk {
    border-radius: 8px;
    background-color: #22c55e;
}
QStatusBar { background-color: #020617; color: #cbd5e1; }
"""


def timestamp(seconds: float) -> str:
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def timestamp_vtt(seconds: float) -> str:
    return timestamp(seconds).replace(",", ".")


def clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def get_model(model_size: str, compute_type: str, cpu_threads: int) -> WhisperModel:
    cpu_threads = max(1, int(cpu_threads or 4))
    key = (model_size, compute_type, cpu_threads)
    if key not in MODEL_CACHE:
        MODEL_CACHE[key] = WhisperModel(
            model_size,
            device="auto",
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
    return MODEL_CACHE[key]


def write_outputs(base_name: str, output_dir: Path, segments_data: list[dict], transcript: str) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_", ".")).strip() or "transcript"
    stem = Path(safe_name).stem

    txt_path = output_dir / f"{stem}.txt"
    srt_path = output_dir / f"{stem}.srt"
    vtt_path = output_dir / f"{stem}.vtt"

    txt_path.write_text(transcript, encoding="utf-8")

    srt_lines: list[str] = []
    for i, seg in enumerate(segments_data, start=1):
        srt_lines.append(str(i))
        srt_lines.append(f"{timestamp(seg['start'])} --> {timestamp(seg['end'])}")
        srt_lines.append(seg["text"].strip())
        srt_lines.append("")
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    vtt_lines = ["WEBVTT", ""]
    for seg in segments_data:
        vtt_lines.append(f"{timestamp_vtt(seg['start'])} --> {timestamp_vtt(seg['end'])}")
        vtt_lines.append(seg["text"].strip())
        vtt_lines.append("")
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")

    return txt_path, srt_path, vtt_path


class TranscriptionWorker(QObject):
    status = Signal(str)
    progress = Signal(int)
    finished = Signal(str, str, str, str, str)
    failed = Signal(str)

    def __init__(
        self,
        file_path: str,
        output_dir: str,
        model_size: str,
        language_name: str,
        task: str,
        compute_type: str,
        beam_size: int,
        vad_filter: bool,
        cpu_threads: int,
        condition_on_previous_text: bool,
    ) -> None:
        super().__init__()
        self.file_path = file_path
        self.output_dir = output_dir
        self.model_size = model_size
        self.language_name = language_name
        self.task = task
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.cpu_threads = cpu_threads
        self.condition_on_previous_text = condition_on_previous_text

    def run(self) -> None:
        try:
            start_time = time.perf_counter()
            self.status.emit("Loading Whisper model. First time may download model files...")
            self.progress.emit(5)
            model = get_model(self.model_size, self.compute_type, self.cpu_threads)

            language = LANGUAGES.get(self.language_name)
            self.status.emit("Transcribing audio/video...")
            self.progress.emit(15)
            segments, info = model.transcribe(
                self.file_path,
                language=language,
                task=self.task.lower(),
                beam_size=int(self.beam_size),
                vad_filter=bool(self.vad_filter),
                condition_on_previous_text=bool(self.condition_on_previous_text),
            )

            segments_data: list[dict] = []
            text_parts: list[str] = []
            for index, seg in enumerate(segments, start=1):
                item = {"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()}
                segments_data.append(item)
                text_parts.append(item["text"])
                if index % 5 == 0:
                    self.status.emit(f"Transcribed {index} segments...")
                    self.progress.emit(min(90, 15 + index))

            transcript = clean_text("\n".join(text_parts))
            self.progress.emit(94)
            self.status.emit("Writing transcript files...")
            output_dir = Path(self.output_dir) if self.output_dir else Path(tempfile.mkdtemp(prefix="transcript_"))
            txt_path, srt_path, vtt_path = write_outputs(
                Path(self.file_path).name,
                output_dir,
                segments_data,
                transcript,
            )

            elapsed = time.perf_counter() - start_time
            detected = getattr(info, "language", "unknown")
            duration = float(getattr(info, "duration", 0.0) or 0.0)
            speed = duration / elapsed if elapsed else 0.0
            status_text = (
                f"Done. Language: {detected}. Duration: {duration:.1f}s. "
                f"Processing: {elapsed:.1f}s ({speed:.2f}x realtime). Segments: {len(segments_data)}."
            )
            self.progress.emit(100)
            self.finished.emit(transcript, status_text, str(txt_path), str(srt_path), str(vtt_path))
        except Exception as exc:  # pragma: no cover - final UI error gate
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class DropLineEdit(QLineEdit):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setPlaceholderText("Drop an audio/video file here or click Browse...")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.setText(path)
            self.file_dropped.emit(path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[TranscriptionWorker] = None
        self.last_files: list[str] = []
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1100, 760)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui()
        self._build_menu()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Choose an audio or video file.")

    def _build_menu(self) -> None:
        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(APP_NAME)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        subtitle = QLabel("No browser. No paid API. Local transcription with faster-whisper.")
        subtitle.setStyleSheet("color: #93c5fd;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        file_box = QGroupBox("Input and output")
        file_layout = QGridLayout(file_box)
        self.file_path = DropLineEdit()
        self.file_path.file_dropped.connect(lambda _: self.status_bar.showMessage("File selected by drag and drop."))
        browse_btn = QPushButton("Browse file")
        browse_btn.clicked.connect(self.browse_file)
        self.output_dir = QLineEdit(str(Path.home() / "Documents" / "LocalWhisperTranscriber"))
        output_btn = QPushButton("Output folder")
        output_btn.clicked.connect(self.browse_output_dir)
        file_layout.addWidget(QLabel("Audio/video file"), 0, 0)
        file_layout.addWidget(self.file_path, 0, 1)
        file_layout.addWidget(browse_btn, 0, 2)
        file_layout.addWidget(QLabel("Save transcripts to"), 1, 0)
        file_layout.addWidget(self.output_dir, 1, 1)
        file_layout.addWidget(output_btn, 1, 2)
        layout.addWidget(file_box)

        settings_box = QGroupBox("Settings")
        settings_layout = QFormLayout(settings_box)
        self.preset = QComboBox()
        self.preset.addItems(PRESETS.keys())
        self.preset.setCurrentText("Balanced")
        self.preset.currentTextChanged.connect(self.apply_preset)
        self.model_size = QComboBox()
        self.model_size.addItems(MODEL_SIZES)
        self.language = QComboBox()
        self.language.addItems(LANGUAGES.keys())
        self.task = QComboBox()
        self.task.addItems(["transcribe", "translate"])
        self.compute_type = QComboBox()
        self.compute_type.addItems(COMPUTE_TYPES)
        self.beam_size = QSpinBox()
        self.beam_size.setRange(1, 10)
        self.cpu_threads = QSpinBox()
        self.cpu_threads.setRange(1, max(2, os.cpu_count() or 4))
        self.cpu_threads.setValue(min(4, os.cpu_count() or 4))
        self.vad_filter = QCheckBox("Skip silence / voice activity filter")
        self.condition_context = QCheckBox("Condition on previous text for long context")
        settings_layout.addRow("Speed / accuracy preset", self.preset)
        settings_layout.addRow("Whisper model", self.model_size)
        settings_layout.addRow("Language", self.language)
        settings_layout.addRow("Task", self.task)
        settings_layout.addRow("Compute type", self.compute_type)
        settings_layout.addRow("Beam size", self.beam_size)
        settings_layout.addRow("CPU threads", self.cpu_threads)
        settings_layout.addRow("Voice activity", self.vad_filter)
        settings_layout.addRow("Long context", self.condition_context)
        layout.addWidget(settings_box)
        self.apply_preset("Balanced")

        action_row = QHBoxLayout()
        self.start_btn = QPushButton("Start transcription")
        self.start_btn.clicked.connect(self.start_transcription)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.clicked.connect(self.clear_output)
        self.open_output_btn = QPushButton("Open output folder")
        self.open_output_btn.setObjectName("secondary")
        self.open_output_btn.clicked.connect(self.open_output_folder)
        action_row.addWidget(self.start_btn)
        action_row.addWidget(self.clear_btn)
        action_row.addWidget(self.open_output_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.transcript = QPlainTextEdit()
        self.transcript.setPlaceholderText("Transcript will appear here...")
        layout.addWidget(self.transcript, stretch=1)

        output_box = QFrame()
        output_layout = QGridLayout(output_box)
        self.txt_path = QLineEdit()
        self.srt_path = QLineEdit()
        self.vtt_path = QLineEdit()
        for field in (self.txt_path, self.srt_path, self.vtt_path):
            field.setReadOnly(True)
        output_layout.addWidget(QLabel("TXT"), 0, 0)
        output_layout.addWidget(self.txt_path, 0, 1)
        output_layout.addWidget(QLabel("SRT"), 1, 0)
        output_layout.addWidget(self.srt_path, 1, 1)
        output_layout.addWidget(QLabel("VTT"), 2, 0)
        output_layout.addWidget(self.vtt_path, 2, 1)
        layout.addWidget(output_box)

        self.setCentralWidget(root)

    def apply_preset(self, preset_name: str) -> None:
        preset = PRESETS[preset_name]
        self.model_size.setCurrentText(preset["model"])
        self.beam_size.setValue(int(preset["beam"]))
        self.vad_filter.setChecked(bool(preset["vad"]))
        self.compute_type.setCurrentText(preset["compute"])

    def browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose audio/video file",
            str(Path.home()),
            "Audio/Video Files (*.mp3 *.wav *.m4a *.mp4 *.mov *.webm *.mkv *.aac *.flac);;All Files (*.*)",
        )
        if path:
            self.file_path.setText(path)

    def browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_dir.text() or str(Path.home()))
        if path:
            self.output_dir.setText(path)

    def validate_inputs(self) -> bool:
        if not self.file_path.text().strip():
            QMessageBox.warning(self, "Missing file", "Choose an audio or video file first.")
            return False
        if not Path(self.file_path.text().strip()).exists():
            QMessageBox.warning(self, "File not found", "The selected file does not exist.")
            return False
        if not self.output_dir.text().strip():
            QMessageBox.warning(self, "Missing output folder", "Choose an output folder.")
            return False
        return True

    def start_transcription(self) -> None:
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "Busy", "A transcription is already running.")
            return
        if not self.validate_inputs():
            return

        self.start_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Starting...")
        self.status_bar.showMessage("Transcription running...")

        self.worker_thread = QThread()
        self.worker = TranscriptionWorker(
            file_path=self.file_path.text().strip(),
            output_dir=self.output_dir.text().strip(),
            model_size=self.model_size.currentText(),
            language_name=self.language.currentText(),
            task=self.task.currentText(),
            compute_type=self.compute_type.currentText(),
            beam_size=self.beam_size.value(),
            vad_filter=self.vad_filter.isChecked(),
            cpu_threads=self.cpu_threads.value(),
            condition_on_previous_text=self.condition_context.isChecked(),
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.status.connect(self.set_status)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.finish_transcription)
        self.worker.failed.connect(self.fail_transcription)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.status_bar.showMessage(text)

    def finish_transcription(self, transcript: str, status: str, txt_path: str, srt_path: str, vtt_path: str) -> None:
        self.transcript.setPlainText(transcript)
        self.status_label.setText(status)
        self.status_bar.showMessage("Finished.")
        self.txt_path.setText(txt_path)
        self.srt_path.setText(srt_path)
        self.vtt_path.setText(vtt_path)
        self.last_files = [txt_path, srt_path, vtt_path]
        self.start_btn.setEnabled(True)
        QMessageBox.information(self, "Transcription complete", status)

    def fail_transcription(self, error: str) -> None:
        self.start_btn.setEnabled(True)
        self.progress.setValue(0)
        self.status_label.setText(error)
        self.status_bar.showMessage("Failed.")
        QMessageBox.critical(self, "Transcription failed", error)

    def clear_output(self) -> None:
        self.transcript.clear()
        self.txt_path.clear()
        self.srt_path.clear()
        self.vtt_path.clear()
        self.progress.setValue(0)
        self.status_label.setText("Ready.")
        self.status_bar.showMessage("Ready.")

    def open_output_folder(self) -> None:
        folder = self.output_dir.text().strip()
        if not folder:
            return
        Path(folder).mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{folder}"')
        else:
            os.system(f'xdg-open "{folder}" >/dev/null 2>&1 &')

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Local Whisper Transcriber",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "A no-browser desktop transcription app for Windows.\n"
            "Built with PySide6 and faster-whisper.\n\n"
            "Audio is processed locally. First model use may download model files.",
        )

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt method name
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Transcription running",
                "A transcription is still running. Close anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
