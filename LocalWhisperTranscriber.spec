# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

# Gradio/FastAPI/faster-whisper have dynamic imports and package metadata.
datas = []
binaries = []
hiddenimports = []

for package in [
    "gradio",
    "gradio_client",
    "safehttpx",
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "requests",
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

# Include Gradio templates/static assets if hook misses them.
try:
    datas += collect_data_files("gradio")
    datas += collect_data_files("gradio_client")
    datas += collect_data_files("safehttpx")
except Exception:
    pass

# safehttpx reads version.txt at runtime; force-include it for PyInstaller.
try:
    import safehttpx
    from pathlib import Path
    safehttpx_dir = Path(safehttpx.__file__).parent
    version_file = safehttpx_dir / "version.txt"
    if version_file.exists():
        datas.append((str(version_file), "safehttpx"))
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
    excludes=[],
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
    console=True,
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
