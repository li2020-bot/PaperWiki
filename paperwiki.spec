# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for PaperWiki
# Build: python3 -m PyInstaller paperwiki.spec

datas = []

hiddenimports = [
    "pydantic",
    "pydantic.deprecated.decorator",
    "jinja2",
    "jinja2.ext",
    "yaml",
    "fitz",
    "ollama",
    "openai",
    "watchdog",
    "watchdog.observers",
    "watchdog.events",
]

a = Analysis(
    ["paperwiki/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="paperwiki",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
