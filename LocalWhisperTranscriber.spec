# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, copy_metadata

# Keep the Windows package focused on what this app actually uses.
# Avoid broad PySide6/Numpy collection: it pulls in Qt WebEngine, SQL drivers,
# examples, and test packages, creating noisy warnings and a much larger build.
datas = []
binaries = []
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "faster_whisper",
    "ctranslate2",
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

# Metadata used by runtime dependency checks. Numpy and PySide6 files/DLLs are handled
# by PyInstaller's standard hooks from the modules imported by app.py.
for package in ["numpy", "PySide6", "shiboken6", "requests", "onnxruntime"]:
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
        "PySide6.QtSql",
        "PySide6.QtQml",
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LocalWhisperTranscriber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LocalWhisperTranscriber",
)
