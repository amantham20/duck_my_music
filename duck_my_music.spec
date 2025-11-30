# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Duck My Music
Build with: pyinstaller duck_my_music.spec
"""

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all pycaw and comtypes data
pycaw_datas, pycaw_binaries, pycaw_hiddenimports = collect_all('pycaw')
comtypes_datas, comtypes_binaries, comtypes_hiddenimports = collect_all('comtypes')

a = Analysis(
    ['duck_my_music_gui.py'],
    pathex=[],
    binaries=pycaw_binaries + comtypes_binaries,
    datas=[
        ('config.json', '.'),
    ] + pycaw_datas + comtypes_datas,
    hiddenimports=[
        'pystray._win32',
        'PIL._tkinter_finder',
        'comtypes.stream',
        'pycaw.pycaw',
        'pycaw.utils',
    ] + pycaw_hiddenimports + comtypes_hiddenimports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DuckMyMusic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if sys.platform == 'win32' else None,
)
