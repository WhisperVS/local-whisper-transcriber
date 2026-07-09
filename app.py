"""Local Whisper Transcriber desktop app.

A true no-browser Windows desktop interface built with PySide6 and faster-whisper.
"""

from __future__ import annotations

import os
import sys
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
    QSizePolicy,
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


def safe_stem(file_name: str) -> str:
    safe_name = "".join(c for c in file_name if c.isalnum() or c in ("-", "_", ".")).strip() or "transcript"
    return Path(safe_name).stem


def build_srt(segments_data: list[dict]) -> str:
    srt_lines: list[str] = []
    for i, seg in enumerate(segments_data, start=1):
        srt_lines.append(str(i))
        srt_lines.append(f"{timestamp(seg['start'])} --> {timestamp(seg['end'])}")
        srt_lines.append(seg["text"].strip())
        srt_lines.append("")
    return "\n".join(srt_lines)


def build_vtt(segments_data: list[dict]) -> str:
    vtt_lines = ["WEBVTT", ""]
    for seg in segments_data:
        vtt_lines.append(f"{timestamp_vtt(seg['start'])} --> {timestamp_vtt(seg['end'])}")
        vtt_lines.append(seg["text"].strip())
        vtt_lines.append("")
    return "\n".join(vtt_lines)


class TranscriptionWorker(QObject):
    status = Signal(str)
    progress = Signal(int)
    finished = Signal(str, str, str, str, str)
    failed = Signal(str)

    def __init__(
        self,
        file_path: str,
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
            task_value = "translate" if self.task.lower().startswith("translate") else "transcribe"
            action_word = "Translating" if task_value == "translate" else "Transcribing"
            self.status.emit(f"{action_word} audio/video...")
            self.progress.emit(15)
            segments, info = model.transcribe(
                self.file_path,
                language=language,
                task=task_value,
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
            self.status.emit("Preparing result for manual save...")
            srt_text = build_srt(segments_data)
            vtt_text = build_vtt(segments_data)

            elapsed = time.perf_counter() - start_time
            detected = getattr(info, "language", "unknown")
            duration = float(getattr(info, "duration", 0.0) or 0.0)
            speed = duration / elapsed if elapsed else 0.0
            action_done = "Translation" if task_value == "translate" else "Transcription"
            status_text = (
                f"{action_done} done. Language: {detected}. Duration: {duration:.1f}s. "
                f"Processing: {elapsed:.1f}s ({speed:.2f}x realtime). Segments: {len(segments_data)}. "
                "Use Save buttons when ready."
            )
            self.progress.emit(100)
            self.finished.emit(transcript, status_text, transcript, srt_text, vtt_text)
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
        self.result_txt = ""
        self.result_srt = ""
        self.result_vtt = ""
        self.default_save_stem = "transcript"
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1100, 760)
        self.setMinimumSize(1000, 760)
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
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(10)

        title = QLabel(APP_NAME)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        subtitle = QLabel("No browser • No paid API • Local transcription with faster-whisper")
        subtitle.setStyleSheet("color: #93c5fd;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        file_box = QGroupBox("Input")
        file_layout = QGridLayout(file_box)
        file_layout.setColumnStretch(1, 1)
        file_layout.setHorizontalSpacing(10)
        file_layout.setVerticalSpacing(8)
        self.file_path = DropLineEdit()
        self.file_path.setMinimumHeight(36)
        self.file_path.file_dropped.connect(lambda _: self.status_bar.showMessage("File selected by drag and drop."))
        browse_btn = QPushButton("Browse file")
        browse_btn.setFixedWidth(120)
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(QLabel("Audio/video"), 0, 0)
        file_layout.addWidget(self.file_path, 0, 1)
        file_layout.addWidget(browse_btn, 0, 2)
        layout.addWidget(file_box)

        settings_box = QGroupBox("Settings")
        settings_layout = QGridLayout(settings_box)
        settings_layout.setHorizontalSpacing(18)
        settings_layout.setVerticalSpacing(8)
        settings_layout.setColumnStretch(1, 1)
        settings_layout.setColumnStretch(3, 1)

        self.preset = QComboBox()
        self.preset.addItems(PRESETS.keys())
        self.preset.setCurrentText("Balanced")
        self.preset.currentTextChanged.connect(self.apply_preset)
        self.model_size = QComboBox()
        self.model_size.addItems(MODEL_SIZES)
        self.language = QComboBox()
        self.language.addItems(LANGUAGES.keys())
        self.task = QComboBox()
        self.task.addItems(["transcribe", "translate to English"])
        self.task.currentTextChanged.connect(self.update_action_labels)
        self.compute_type = QComboBox()
        self.compute_type.addItems(COMPUTE_TYPES)
        self.beam_size = QSpinBox()
        self.beam_size.setRange(1, 10)
        self.cpu_threads = QSpinBox()
        self.cpu_threads.setRange(1, max(2, os.cpu_count() or 4))
        self.cpu_threads.setValue(min(4, os.cpu_count() or 4))
        self.vad_filter = QCheckBox("Skip silence")
        self.condition_context = QCheckBox("Use previous text context")

        # Keep beginner workflow clean. The preset controls compute type, beam size,
        # and CPU threads behind the scenes; those advanced controls remain available
        # in code but are not shown in the main UI.
        self.compute_type.setCurrentText("int8")
        self.beam_size.setValue(3)
        self.condition_context.setChecked(False)

        compact_widgets = [self.preset, self.model_size, self.language, self.task]
        for widget in compact_widgets:
            widget.setMinimumHeight(34)
            widget.setMaximumWidth(360)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        def add_setting(row: int, col: int, label_text: str, widget: QWidget) -> None:
            label = QLabel(label_text)
            label.setMinimumWidth(90)
            settings_layout.addWidget(label, row, col * 2)
            settings_layout.addWidget(widget, row, col * 2 + 1)

        add_setting(0, 0, "Preset", self.preset)
        add_setting(0, 1, "Language", self.language)
        add_setting(1, 0, "Model", self.model_size)
        add_setting(1, 1, "Task", self.task)
        settings_layout.addWidget(self.vad_filter, 2, 0, 1, 2)
        helper = QLabel("Normal use: choose file → keep Balanced → click Start. Translate mode outputs English only.")
        helper.setStyleSheet("color: #94a3b8;")
        helper.setWordWrap(True)
        settings_layout.addWidget(helper, 2, 2, 1, 2)
        layout.addWidget(settings_box)
        self.apply_preset("Balanced")

        control_box = QGroupBox("Run")
        control_layout = QGridLayout(control_box)
        control_layout.setColumnStretch(3, 1)
        self.start_btn = QPushButton("Start transcription")
        self.start_btn.setMinimumWidth(150)
        self.start_btn.clicked.connect(self.start_transcription)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.setFixedWidth(90)
        self.clear_btn.clicked.connect(self.clear_output)
        self.save_txt_btn = QPushButton("Save TXT")
        self.save_txt_btn.setObjectName("secondary")
        self.save_txt_btn.clicked.connect(lambda: self.save_result("txt"))
        self.save_srt_btn = QPushButton("Save SRT")
        self.save_srt_btn.setObjectName("secondary")
        self.save_srt_btn.clicked.connect(lambda: self.save_result("srt"))
        self.save_vtt_btn = QPushButton("Save VTT")
        self.save_vtt_btn.setObjectName("secondary")
        self.save_vtt_btn.clicked.connect(lambda: self.save_result("vtt"))
        self.set_save_buttons_enabled(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMinimumHeight(22)
        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(24)
        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.clear_btn, 0, 1)
        control_layout.addWidget(self.progress, 0, 2, 1, 4)
        control_layout.addWidget(self.status_label, 1, 0, 1, 6)
        layout.addWidget(control_box)

        transcript_box = QGroupBox("Transcript")
        transcript_layout = QVBoxLayout(transcript_box)
        transcript_layout.setContentsMargins(14, 18, 14, 14)
        self.transcript = QPlainTextEdit()
        self.transcript.setPlaceholderText("Transcript or English translation will appear here...")
        self.transcript.setMinimumHeight(110)
        self.transcript.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        transcript_layout.addWidget(self.transcript)
        layout.addWidget(transcript_box, stretch=1)

        save_widget = QWidget()
        save_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        save_row = QHBoxLayout(save_widget)
        save_row.setContentsMargins(8, 0, 8, 0)
        save_row.setSpacing(8)
        save_label = QLabel("Manual save:")
        save_label.setStyleSheet("color: #94a3b8;")
        save_row.addWidget(save_label)
        save_row.addWidget(self.save_txt_btn)
        save_row.addWidget(self.save_srt_btn)
        save_row.addWidget(self.save_vtt_btn)
        save_row.addStretch(1)
        layout.addWidget(save_widget)

        self.setCentralWidget(root)
        self.update_action_labels(self.task.currentText())

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

    def validate_inputs(self) -> bool:
        if not self.file_path.text().strip():
            QMessageBox.warning(self, "Missing file", "Choose an audio or video file first.")
            return False
        if not Path(self.file_path.text().strip()).exists():
            QMessageBox.warning(self, "File not found", "The selected file does not exist.")
            return False
        return True

    def start_transcription(self) -> None:
        if self.is_transcription_running():
            QMessageBox.information(self, "Busy", "A transcription is already running.")
            return
        if not self.validate_inputs():
            return

        self.start_btn.setEnabled(False)
        self.set_save_buttons_enabled(False)
        self.result_txt = ""
        self.result_srt = ""
        self.result_vtt = ""
        self.default_save_stem = safe_stem(Path(self.file_path.text().strip()).name)
        self.progress.setValue(0)
        action_noun = "Translation" if self.task.currentText().startswith("translate") else "Transcription"
        self.status_label.setText("Starting...")
        self.status_bar.showMessage(f"{action_noun} running...")

        self.worker_thread = QThread()
        self.worker = TranscriptionWorker(
            file_path=self.file_path.text().strip(),
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
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.cleanup_worker_state)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.status_bar.showMessage(text)

    def is_transcription_running(self) -> bool:
        if self.worker_thread is None:
            return False
        try:
            return bool(self.worker_thread.isRunning())
        except RuntimeError:
            # Qt object was already deleted; clear stale Python references.
            self.cleanup_worker_state()
            return False

    def cleanup_worker_state(self) -> None:
        self.worker = None
        self.worker_thread = None
        self.start_btn.setEnabled(True)

    def finish_transcription(self, transcript: str, status: str, txt_text: str, srt_text: str, vtt_text: str) -> None:
        self.result_txt = txt_text
        self.result_srt = srt_text
        self.result_vtt = vtt_text
        self.transcript.setPlainText(transcript)
        self.status_label.setText(status)
        self.status_bar.showMessage("Finished. Result is not saved yet.")
        self.set_save_buttons_enabled(bool(transcript))
        self.start_btn.setEnabled(True)
        QMessageBox.information(self, "Result ready", status)

    def fail_transcription(self, error: str) -> None:
        self.start_btn.setEnabled(True)
        self.progress.setValue(0)
        self.status_label.setText(error)
        self.status_bar.showMessage("Failed.")
        QMessageBox.critical(self, "Transcription failed", error)

    def clear_output(self) -> None:
        self.transcript.clear()
        self.result_txt = ""
        self.result_srt = ""
        self.result_vtt = ""
        self.set_save_buttons_enabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Ready.")
        self.status_bar.showMessage("Ready.")

    def set_save_buttons_enabled(self, enabled: bool) -> None:
        for button in (self.save_txt_btn, self.save_srt_btn, self.save_vtt_btn):
            button.setEnabled(enabled)

    def update_action_labels(self, task: str) -> None:
        if not hasattr(self, "start_btn"):
            return
        has_status_bar = hasattr(self, "status_bar")
        if task.startswith("translate"):
            self.start_btn.setText("Start translation")
            if has_status_bar:
                self.status_bar.showMessage("Translate to English mode: Whisper can only translate speech into English.")
        else:
            self.start_btn.setText("Start transcription")
            if has_status_bar:
                self.status_bar.showMessage("Transcribe mode: Whisper will write the original spoken language.")

    def save_result(self, kind: str) -> None:
        content_by_kind = {
            "txt": self.result_txt,
            "srt": self.result_srt,
            "vtt": self.result_vtt,
        }
        content = content_by_kind.get(kind, "")
        if not content:
            QMessageBox.information(self, "Nothing to save", "Run transcription or translation first.")
            return
        default_path = str(Path.home() / "Documents" / f"{self.default_save_stem}.{kind}")
        filters = {
            "txt": "Text file (*.txt)",
            "srt": "SubRip subtitles (*.srt)",
            "vtt": "WebVTT subtitles (*.vtt)",
        }
        path, _ = QFileDialog.getSaveFileName(self, f"Save {kind.upper()}", default_path, filters[kind])
        if not path:
            return
        if not path.lower().endswith(f".{kind}"):
            path = f"{path}.{kind}"
        Path(path).write_text(content, encoding="utf-8")
        self.status_bar.showMessage(f"Saved {kind.upper()} to {path}")
        QMessageBox.information(self, "Saved", f"Saved {kind.upper()} file:\n{path}")

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
        if self.is_transcription_running():
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
