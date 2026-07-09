import os
import tempfile
import time
from pathlib import Path
from typing import Tuple

import gradio as gr
from faster_whisper import WhisperModel

# Compatibility guard for some Gradio / gradio_client / FastAPI dependency combinations.
# On some Windows installs, Gradio's internal API-info route crashes when a JSON schema
# contains boolean additionalProperties. The UI does not need this route for normal use,
# so we make the schema converter tolerate bool values instead of crashing.
try:
    import gradio_client.utils as _gradio_client_utils

    _original_json_schema_to_python_type = _gradio_client_utils._json_schema_to_python_type

    def _safe_json_schema_to_python_type(schema, defs=None):
        if isinstance(schema, bool):
            return "Any"
        return _original_json_schema_to_python_type(schema, defs)

    _gradio_client_utils._json_schema_to_python_type = _safe_json_schema_to_python_type
except Exception:
    pass

APP_TITLE = "Local Whisper Transcriber"
APP_DESCRIPTION = "Private local transcription for Windows. No paid API key required."

MODEL_CACHE = {}

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
SPEED_PRESETS = {
    "Fast draft": {"model": "base", "beam": 1, "vad": True, "compute": "int8"},
    "Balanced": {"model": "small", "beam": 3, "vad": True, "compute": "int8"},
    "High accuracy": {"model": "medium", "beam": 5, "vad": True, "compute": "int8"},
    "Maximum accuracy / slow": {"model": "large-v3", "beam": 5, "vad": True, "compute": "int8"},
}
THEMES = ["Midnight", "Frost", "Solar", "Clean Light"]


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


def get_model(model_size: str, compute_type: str, cpu_threads: int) -> WhisperModel:
    cpu_threads = max(1, int(cpu_threads or 4))
    key = (model_size, compute_type, cpu_threads)
    if key not in MODEL_CACHE:
        # device="auto" uses GPU if available, otherwise CPU.
        MODEL_CACHE[key] = WhisperModel(
            model_size,
            device="auto",
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
    return MODEL_CACHE[key]


def clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def write_outputs(base_name: str, segments_data: list, transcript: str) -> Tuple[str, str, str]:
    out_dir = Path(tempfile.mkdtemp(prefix="transcript_"))
    safe_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_", ".")).strip() or "transcript"
    stem = Path(safe_name).stem

    txt_path = out_dir / f"{stem}.txt"
    srt_path = out_dir / f"{stem}.srt"
    vtt_path = out_dir / f"{stem}.vtt"

    txt_path.write_text(transcript, encoding="utf-8")

    srt_lines = []
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

    return str(txt_path), str(srt_path), str(vtt_path)


def apply_preset(preset_name: str):
    preset = SPEED_PRESETS[preset_name]
    return preset["model"], preset["beam"], preset["vad"], preset["compute"]


def theme_style(theme_name: str) -> str:
    palettes = {
        "Midnight": {
            "bg": "#080b14", "panel": "rgba(17,24,39,.86)", "card": "rgba(30,41,59,.78)",
            "text": "#e5e7eb", "muted": "#9ca3af", "accent": "#8b5cf6", "accent2": "#22d3ee",
        },
        "Frost": {
            "bg": "#07111f", "panel": "rgba(15,23,42,.84)", "card": "rgba(30,64,175,.24)",
            "text": "#eff6ff", "muted": "#bfdbfe", "accent": "#38bdf8", "accent2": "#a78bfa",
        },
        "Solar": {
            "bg": "#140b05", "panel": "rgba(41,23,12,.86)", "card": "rgba(120,53,15,.35)",
            "text": "#fff7ed", "muted": "#fed7aa", "accent": "#f97316", "accent2": "#facc15",
        },
        "Clean Light": {
            "bg": "#f8fafc", "panel": "rgba(255,255,255,.92)", "card": "rgba(241,245,249,.95)",
            "text": "#0f172a", "muted": "#475569", "accent": "#2563eb", "accent2": "#14b8a6",
        },
    }
    p = palettes.get(theme_name, palettes["Midnight"])
    return f"""
<style>
:root {{
  --lt-bg: {p['bg']};
  --lt-panel: {p['panel']};
  --lt-card: {p['card']};
  --lt-text: {p['text']};
  --lt-muted: {p['muted']};
  --lt-accent: {p['accent']};
  --lt-accent2: {p['accent2']};
}}
.gradio-container {{
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--lt-accent) 24%, transparent), transparent 32rem),
    radial-gradient(circle at top right, color-mix(in srgb, var(--lt-accent2) 22%, transparent), transparent 30rem),
    var(--lt-bg) !important;
  color: var(--lt-text) !important;
}}
#hero, #main-card {{
  border: 1px solid color-mix(in srgb, var(--lt-accent) 30%, transparent);
  border-radius: 24px;
  padding: 22px;
  background: var(--lt-panel);
  box-shadow: 0 22px 70px rgba(0,0,0,.32);
}}
#hero h1 {{
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 1;
  margin-bottom: .45rem;
  background: linear-gradient(90deg, var(--lt-accent), var(--lt-accent2));
  -webkit-background-clip: text;
  color: transparent;
}}
#hero p, .hint {{ color: var(--lt-muted); font-size: 1rem; }}
.stat-card {{
  background: var(--lt-card);
  border: 1px solid color-mix(in srgb, var(--lt-accent2) 24%, transparent);
  border-radius: 18px;
  padding: 14px 16px;
}}
button.primary, .primary button {{
  border-radius: 999px !important;
  background: linear-gradient(90deg, var(--lt-accent), var(--lt-accent2)) !important;
  border: none !important;
}}
textarea, input, select {{ border-radius: 14px !important; }}
</style>
"""


def transcribe_file(
    file_path: str,
    model_size: str,
    language_name: str,
    task: str,
    compute_type: str,
    beam_size: int,
    vad_filter: bool,
    cpu_threads: int,
    condition_on_previous_text: bool,
) -> Tuple[str, str, str, str, str]:
    if not file_path:
        raise gr.Error("Upload an audio or video file first.")

    start_time = time.perf_counter()
    language = LANGUAGES.get(language_name)
    model = get_model(model_size, compute_type, cpu_threads)

    segments, info = model.transcribe(
        file_path,
        language=language,
        task=task.lower(),
        beam_size=int(beam_size),
        vad_filter=bool(vad_filter),
        condition_on_previous_text=bool(condition_on_previous_text),
    )

    segments_data = []
    text_parts = []
    for seg in segments:
        item = {"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()}
        segments_data.append(item)
        text_parts.append(item["text"])

    elapsed = time.perf_counter() - start_time
    transcript = clean_text("\n".join(text_parts))
    detected = getattr(info, "language", "unknown")
    duration = float(getattr(info, "duration", 0.0) or 0.0)
    speed = duration / elapsed if elapsed else 0.0
    status = (
        f"Done. Detected language: {detected}. Audio/video duration: {duration:.1f}s. "
        f"Processing time: {elapsed:.1f}s ({speed:.2f}x realtime). Segments: {len(segments_data)}."
    )

    txt_path, srt_path, vtt_path = write_outputs(Path(file_path).name, segments_data, transcript)
    return transcript, status, txt_path, srt_path, vtt_path


def build_ui() -> gr.Blocks:
    css = """
    #hero, #main-card { max-width: 1180px; margin: 0 auto; }
    .footer-note { text-align: center; opacity: .78; }
    """
    with gr.Blocks(title=APP_TITLE, css=css, theme=gr.themes.Soft()) as demo:
        live_theme = gr.HTML(theme_style("Midnight"))

        with gr.Column(elem_id="hero"):
            gr.Markdown(
                f"# {APP_TITLE}\n"
                f"{APP_DESCRIPTION}\n\n"
                "**Private by design:** files are processed on this PC. First use downloads the selected Whisper model."
            )
            with gr.Row():
                gr.HTML("<div class='stat-card'><b>Fast mode</b><br><span class='hint'>Base model + beam 1</span></div>")
                gr.HTML("<div class='stat-card'><b>Balanced mode</b><br><span class='hint'>Good daily default</span></div>")
                gr.HTML("<div class='stat-card'><b>Subtitle export</b><br><span class='hint'>TXT / SRT / VTT</span></div>")

        with gr.Column(elem_id="main-card"):
            with gr.Row():
                theme_picker = gr.Dropdown(THEMES, value="Midnight", label="Theme")
                preset = gr.Dropdown(list(SPEED_PRESETS.keys()), value="Balanced", label="Speed / accuracy preset")

            file_input = gr.File(label="Drop audio/video here", file_types=["audio", "video"], type="filepath")

            with gr.Row():
                model_size = gr.Dropdown(MODEL_SIZES, value="small", label="Whisper model")
                language = gr.Dropdown(list(LANGUAGES.keys()), value="Auto detect", label="Language")
                task = gr.Radio(["transcribe", "translate"], value="transcribe", label="Task")

            with gr.Accordion("Advanced controls", open=False):
                with gr.Row():
                    compute_type = gr.Dropdown(COMPUTE_TYPES, value="int8", label="Compute type")
                    beam_size = gr.Slider(1, 10, value=3, step=1, label="Beam size / accuracy")
                    cpu_threads = gr.Slider(1, max(2, os.cpu_count() or 4), value=min(4, os.cpu_count() or 4), step=1, label="CPU threads")
                with gr.Row():
                    vad_filter = gr.Checkbox(value=True, label="Skip silence / voice activity filter")
                    condition_on_previous_text = gr.Checkbox(
                        value=False,
                        label="Condition on previous text (slower, can improve long context)",
                    )

            transcribe_btn = gr.Button("Transcribe", variant="primary", elem_classes=["primary"])
            status = gr.Textbox(label="Status", interactive=False)
            transcript = gr.Textbox(label="Transcript", lines=18, show_copy_button=True)

            with gr.Row():
                txt_file = gr.File(label="Download TXT")
                srt_file = gr.File(label="Download SRT subtitles")
                vtt_file = gr.File(label="Download VTT subtitles")

        gr.Markdown(
            "<p class='footer-note'>Tip: for speed use Fast draft + manually selected language. For accuracy use Balanced or High accuracy.</p>"
        )

        theme_picker.change(fn=theme_style, inputs=theme_picker, outputs=live_theme)
        preset.change(fn=apply_preset, inputs=preset, outputs=[model_size, beam_size, vad_filter, compute_type])
        transcribe_btn.click(
            fn=transcribe_file,
            inputs=[
                file_input,
                model_size,
                language,
                task,
                compute_type,
                beam_size,
                vad_filter,
                cpu_threads,
                condition_on_previous_text,
            ],
            outputs=[transcript, status, txt_file, srt_file, vtt_file],
        )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_api=False,
    )
