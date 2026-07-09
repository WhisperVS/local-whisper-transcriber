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
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
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
    QScrollArea,
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
MODEL_HELP = {
    "tiny": "tiny: fastest, weakest accuracy. Good only for quick tests or very weak PCs.",
    "base": "base: fast rough draft. Better than tiny, but still for speed more than quality.",
    "small": "small: recommended default. Best balance for daily transcription.",
    "medium": "medium: more accurate, slower. Use for important or noisy audio.",
    "large-v3": "large-v3: best accuracy, slowest/heaviest. Use when quality matters most.",
}
PRESETS = {
    "Fast draft": {"model": "base", "beam": 1, "vad": True, "compute": "int8"},
    "Balanced": {"model": "small", "beam": 3, "vad": True, "compute": "int8"},
    "High accuracy": {"model": "medium", "beam": 5, "vad": True, "compute": "int8"},
    "Maximum accuracy / slow": {"model": "large-v3", "beam": 5, "vad": True, "compute": "int8"},
}
MODEL_CACHE: dict[tuple[str, str, int], WhisperModel] = {}


DARK_STYLE = """
QMainWindow {
    background-color: #070b16;
    color: #e5e7eb;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10.5pt;
}
QWidget {
    color: #e5e7eb;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10.5pt;
}
QWidget#centralRoot {
    background-color: #070b16;
}
QScrollArea#mainScroll {
    background-color: #070b16;
    border: 0;
}
QScrollArea#mainScroll > QWidget > QWidget {
    background-color: #070b16;
}
QWidget#contentPanel {
    background-color: transparent;
}
QWidget#hero {
    background-color: #0f172a;
    border: 1px solid #1e3a5f;
    border-radius: 16px;
}
QLabel {
    background-color: transparent;
}
QLabel#title {
    color: #f8fafc;
    font-size: 19pt;
    font-weight: 800;
}
QLabel#subtitle, QLabel#hint, QLabel#model_help, QLabel#save_label, QLabel#field_label {
    color: #9fb8d8;
}
QLabel#section_title {
    color: #bfdbfe;
    font-size: 10pt;
    font-weight: 800;
}
QGroupBox#card {
    border: 1px solid #26364f;
    border-radius: 14px;
    margin-top: 0;
    padding: 0;
    background-color: #101827;
}
QGroupBox#card::title {
    height: 0;
    color: transparent;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #050816;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 8px 10px;
    color: #f8fafc;
    selection-background-color: #2563eb;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #60a5fa;
}
QPlainTextEdit {
    font-family: Consolas, Cascadia Mono, monospace;
    line-height: 125%;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QPushButton {
    background-color: #2563eb;
    border: 0;
    border-radius: 10px;
    color: white;
    padding: 10px 16px;
    font-weight: 700;
}
QPushButton:hover { background-color: #1d4ed8; }
QPushButton:pressed { background-color: #1e40af; }
QPushButton:disabled { background-color: #243044; color: #94a3b8; }
QPushButton#primary { background-color: #2563eb; }
QPushButton#secondary { background-color: #2d3b50; }
QPushButton#secondary:hover { background-color: #3b4b63; }
QPushButton#danger { background-color: #dc2626; }
QCheckBox {
    spacing: 8px;
    color: #dbeafe;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #050816;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border: 1px solid #60a5fa;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 10px;
    background-color: #050816;
    text-align: center;
    color: #dbeafe;
    font-weight: 600;
}
QProgressBar::chunk {
    border-radius: 9px;
    background-color: #22c55e;
}
QMenuBar {
    background-color: #070b16;
    color: #e5e7eb;
}
QMenuBar::item:selected { background-color: #1e293b; }
QStatusBar {
    background-color: #050816;
    color: #cbd5e1;
    border-top: 1px solid #1e293b;
}
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
        self.resize(1000, 760)
        self.setMinimumSize(640, 520)
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
        root.setObjectName("centralRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_container = QWidget()
        scroll_container.setObjectName("centralRoot")
        outer_layout = QHBoxLayout(scroll_container)
        outer_layout.setContentsMargins(18, 14, 18, 12)
        outer_layout.setSpacing(0)

        content = QWidget()
        content.setObjectName("contentPanel")
        content.setMaximumWidth(1280)
        content.setMinimumHeight(760)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        outer_layout.addWidget(content, stretch=1)
        scroll_area.setWidget(scroll_container)
        root_layout.addWidget(scroll_area)

        hero = QWidget()
        hero.setObjectName("hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 14, 18, 14)
        hero_layout.setSpacing(4)
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        subtitle = QLabel("Private local transcription • No browser • No paid API")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        file_box = QGroupBox()
        file_box.setObjectName("card")
        file_box.setMinimumHeight(112)
        file_card_layout = QVBoxLayout(file_box)
        file_card_layout.setContentsMargins(18, 14, 18, 16)
        file_card_layout.setSpacing(12)
        file_title = QLabel("1  Choose file")
        file_title.setObjectName("section_title")
        file_card_layout.addWidget(file_title)
        file_layout = QGridLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setColumnStretch(1, 1)
        file_layout.setHorizontalSpacing(12)
        file_layout.setVerticalSpacing(8)
        self.file_path = DropLineEdit()
        self.file_path.setMinimumHeight(42)
        self.file_path.file_dropped.connect(lambda _: self.status_bar.showMessage("File selected by drag and drop."))
        browse_btn = QPushButton("Browse file")
        browse_btn.setMinimumWidth(130)
        browse_btn.setMinimumHeight(42)
        browse_btn.clicked.connect(self.browse_file)
        file_label = QLabel("Audio/video")
        file_label.setObjectName("field_label")
        file_label.setMinimumWidth(92)
        file_layout.addWidget(file_label, 0, 0)
        file_layout.addWidget(self.file_path, 0, 1)
        file_layout.addWidget(browse_btn, 0, 2)
        file_card_layout.addLayout(file_layout)
        layout.addWidget(file_box)

        settings_box = QGroupBox()
        settings_box.setObjectName("card")
        settings_box.setMinimumHeight(220)
        settings_card_layout = QVBoxLayout(settings_box)
        settings_card_layout.setContentsMargins(18, 14, 18, 16)
        settings_card_layout.setSpacing(12)
        settings_title = QLabel("2  Settings")
        settings_title.setObjectName("section_title")
        settings_card_layout.addWidget(settings_title)
        self.settings_layout = QGridLayout()
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_layout.setHorizontalSpacing(18)
        self.settings_layout.setVerticalSpacing(14)
        self.settings_layout.setColumnStretch(0, 1)
        self.settings_layout.setColumnStretch(1, 1)

        self.preset = QComboBox()
        self.preset.addItems(PRESETS.keys())
        self.preset.setCurrentText("Balanced")
        self.preset.currentTextChanged.connect(self.apply_preset)
        self.model_size = QComboBox()
        self.model_size.addItems(MODEL_SIZES)
        self.model_size.currentTextChanged.connect(self.update_model_help)
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
            widget.setMinimumHeight(38)
            widget.setMaximumWidth(440)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        def make_setting(label_text: str, widget: QWidget) -> QWidget:
            setting = QWidget()
            setting_layout = QVBoxLayout(setting)
            setting_layout.setContentsMargins(0, 0, 0, 0)
            setting_layout.setSpacing(5)
            label = QLabel(label_text)
            label.setObjectName("field_label")
            setting_layout.addWidget(label)
            setting_layout.addWidget(widget)
            return setting

        self.setting_preset = make_setting("Preset", self.preset)
        self.setting_language = make_setting("Language", self.language)
        self.setting_model = make_setting("Model", self.model_size)
        self.setting_task = make_setting("Task", self.task)
        self.model_help = QLabel()
        self.model_help.setObjectName("model_help")
        self.model_help.setWordWrap(True)
        self.model_help.setToolTip("Bigger Whisper models are usually more accurate, but slower and heavier.")
        self._settings_compact: Optional[bool] = None
        self._arrange_settings(compact=False)
        settings_card_layout.addLayout(self.settings_layout)
        layout.addWidget(settings_box)
        self.apply_preset("Balanced")

        control_box = QGroupBox()
        control_box.setObjectName("card")
        control_box.setMinimumHeight(132)
        control_card_layout = QVBoxLayout(control_box)
        control_card_layout.setContentsMargins(18, 14, 18, 16)
        control_card_layout.setSpacing(12)
        control_title = QLabel("3  Run")
        control_title.setObjectName("section_title")
        control_card_layout.addWidget(control_title)
        control_layout = QGridLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setHorizontalSpacing(12)
        control_layout.setVerticalSpacing(10)
        control_layout.setColumnStretch(2, 1)
        self.start_btn = QPushButton("Start transcription")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumWidth(170)
        self.start_btn.setMinimumHeight(42)
        self.start_btn.clicked.connect(self.start_transcription)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.setMinimumWidth(100)
        self.clear_btn.setMinimumHeight(42)
        self.clear_btn.clicked.connect(self.clear_output)
        self.save_txt_btn = QPushButton("Save TXT")
        self.save_txt_btn.setObjectName("secondary")
        self.save_txt_btn.setMinimumHeight(38)
        self.save_txt_btn.clicked.connect(lambda: self.save_result("txt"))
        self.save_srt_btn = QPushButton("Save SRT")
        self.save_srt_btn.setObjectName("secondary")
        self.save_srt_btn.setMinimumHeight(38)
        self.save_srt_btn.clicked.connect(lambda: self.save_result("srt"))
        self.save_vtt_btn = QPushButton("Save VTT")
        self.save_vtt_btn.setObjectName("secondary")
        self.save_vtt_btn.setMinimumHeight(38)
        self.save_vtt_btn.clicked.connect(lambda: self.save_result("vtt"))
        self.set_save_buttons_enabled(False)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMinimumHeight(26)
        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("hint")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(26)
        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.clear_btn, 0, 1)
        control_layout.addWidget(self.progress, 0, 2, 1, 4)
        control_layout.addWidget(self.status_label, 1, 0, 1, 6)
        control_card_layout.addLayout(control_layout)
        layout.addWidget(control_box)

        transcript_box = QGroupBox()
        transcript_box.setObjectName("card")
        transcript_box.setMinimumHeight(150)
        transcript_layout = QVBoxLayout(transcript_box)
        transcript_layout.setContentsMargins(18, 14, 18, 16)
        transcript_layout.setSpacing(12)
        transcript_title = QLabel("4  Transcript")
        transcript_title.setObjectName("section_title")
        transcript_layout.addWidget(transcript_title)
        self.transcript = QPlainTextEdit()
        self.transcript.setPlaceholderText("Transcript or English translation will appear here...")
        self.transcript.setMinimumHeight(72)
        self.transcript.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        transcript_layout.addWidget(self.transcript)
        layout.addWidget(transcript_box, stretch=1)

        save_widget = QWidget()
        save_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        save_row = QHBoxLayout(save_widget)
        save_row.setContentsMargins(8, 0, 8, 0)
        save_row.setSpacing(10)
        save_label = QLabel("Save result:")
        save_label.setObjectName("save_label")
        save_row.addWidget(save_label)
        save_row.addWidget(self.save_txt_btn)
        save_row.addWidget(self.save_srt_btn)
        save_row.addWidget(self.save_vtt_btn)
        save_row.addStretch(1)
        layout.addWidget(save_widget)

        self.setCentralWidget(root)
        self.update_action_labels(self.task.currentText())
        self._apply_responsive_layout()

    def _clear_layout(self, layout: QGridLayout) -> None:
        while layout.count():
            layout.takeAt(0)

    def _arrange_settings(self, compact: bool) -> None:
        if getattr(self, "_settings_compact", None) == compact:
            return
        self._settings_compact = compact
        self._clear_layout(self.settings_layout)
        if compact:
            self.settings_layout.setColumnStretch(0, 1)
            self.settings_layout.setColumnStretch(1, 0)
            self.settings_layout.addWidget(self.setting_preset, 0, 0, 1, 2)
            self.settings_layout.addWidget(self.setting_language, 1, 0, 1, 2)
            self.settings_layout.addWidget(self.setting_model, 2, 0, 1, 2)
            self.settings_layout.addWidget(self.setting_task, 3, 0, 1, 2)
            self.settings_layout.addWidget(self.vad_filter, 4, 0, 1, 2)
            self.settings_layout.addWidget(self.model_help, 5, 0, 1, 2)
        else:
            self.settings_layout.setColumnStretch(0, 1)
            self.settings_layout.setColumnStretch(1, 1)
            self.settings_layout.addWidget(self.setting_preset, 0, 0)
            self.settings_layout.addWidget(self.setting_language, 0, 1)
            self.settings_layout.addWidget(self.setting_model, 1, 0)
            self.settings_layout.addWidget(self.setting_task, 1, 1)
            self.settings_layout.addWidget(self.vad_filter, 2, 0, 1, 1)
            self.settings_layout.addWidget(self.model_help, 3, 0, 1, 2)

    def _apply_responsive_layout(self) -> None:
        if not hasattr(self, "settings_layout"):
            return
        compact = self.width() < 820
        self._arrange_settings(compact=compact)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def apply_preset(self, preset_name: str) -> None:
        preset = PRESETS[preset_name]
        self.model_size.setCurrentText(preset["model"])
        self.beam_size.setValue(int(preset["beam"]))
        self.vad_filter.setChecked(bool(preset["vad"]))
        self.compute_type.setCurrentText(preset["compute"])
        self.update_model_help(self.model_size.currentText())

    def update_model_help(self, model_size: str) -> None:
        if not hasattr(self, "model_help"):
            return
        self.model_help.setText(MODEL_HELP.get(model_size, "Choose a Whisper model size."))

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
