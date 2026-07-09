# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, copy_metadata

# Package only the modules used by the desktop app, but be conservative for the
# Whisper runtime. Missing ML DLLs can make a windowed EXE close immediately.
datas = []
binaries = []
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "onnxruntime.capi._pybind_state",
    "onnxruntime.capi.onnxruntime_pybind11_state",
    "tokenizers",
    "huggingface_hub",
    "av",
    "numpy",
    "tqdm",
]

for package in [
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "av",
    "tqdm",
]:
    try:
        package_datas, package_binaries, package_hidden = collect_all(package)
        datas += package_datas
        binaries += package_binaries
        hiddenimports += package_hidden
    except Exception:
        pass
    try:
        datas += copy_metadata(package)
    except Exception:
        pass

# Metadata used by runtime dependency checks. Numpy and PySide6 files/DLLs are
# handled by PyInstaller's standard hooks from the modules imported by app.py.
for package in ["numpy", "PySide6", "shiboken6", "requests", "certifi", "packaging"]:
    try:
        datas += copy_metadata(package)
    except Exception:
        pass

block_cipher = None


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "gradio",
        "gradio_client",
        "fastapi",
        "uvicorn",
        "starlette",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "tkinter",
        "pytest",
        "numpy.tests",
        "numpy.f2py.tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

windowed_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LocalWhisperTranscriber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Console build for diagnostics. If the normal EXE silently closes, run this
# from run_exe_debug.bat to capture the real Python/Qt error in exe_debug_log.txt.
debug_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LocalWhisperTranscriberDebug",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    windowed_exe,
    debug_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LocalWhisperTranscriber",
)
