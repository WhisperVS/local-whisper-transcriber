# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

# PySide6 and faster-whisper use dynamic imports and package metadata.
datas = []
binaries = []
hiddenimports = []

for package in [
    "PySide6",
    "shiboken6",
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "numpy",
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

try:
    datas += collect_data_files("PySide6")
    datas += collect_data_files("faster_whisper")
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
    excludes=["gradio", "gradio_client", "fastapi", "uvicorn", "starlette"],
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
