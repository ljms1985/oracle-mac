# PyInstaller spec for Oracle for macOS — builds a standalone Oracle.app.
#
# Build ON A MAC ONLY (a .app cannot be built on Windows or Linux):
#   pip3 install pyinstaller
#   pyinstaller oracle-mac.spec
# Output: dist/Oracle.app  (run it by double-clicking, or from Terminal)
#
# This spec was NOT built in this package — no .app was produced here
# (see BUILD_NOTES_MAC.md). The source-tree install in
# ORACLE_SETUP_MAC.md is the supported route; the .app is a convenience.
# tkinter is bundled by PyInstaller automatically on macOS; the data
# files below are the docs the GUI/setup text refers to.

# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('ORACLE_SETUP_MAC.md', '.'),
        ('SETUP_GUIDE.md', '.'),
        ('3D_KNOWLEDGE.md', '.'),
        ('SECURITY_KNOWLEDGE.md', '.'),
        ('AVATAR_NOTES_MAC.md', '.'),
        ('BUILD_NOTES_MAC.md', '.'),
        # Lorenza's chosen Muse avatar (red-and-black anime). gui.py
        # loads assets/avatar.png, falling back to avatar.png — both
        # are bundled so the face shows in the frozen .app.
        ('assets/avatar.png', 'assets'),
        ('avatar.png', '.'),
        # Sample STL prints (design3d.py writes new ones to prints/).
        ('prints', 'prints'),
    ],
    hiddenimports=[
        'agent', 'computer', 'voice', 'camera', 'monitor',
        'email_alerts', 'identity', 'repair', 'design3d', 'security',
        'memory_import', 'PIL', 'PIL.Image', 'PIL.ImageTk',
    ],
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
    name='Oracle',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
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
    name='Oracle',
)
app = BUNDLE(
    coll,
    name='Oracle.app',
    icon=None,
    bundle_identifier='com.lorenza.oracle',
    info_plist={
        'NSMicrophoneUsageDescription': 'Oracle listens for your voice when always-listening is turned on in the GUI.',
        'NSCameraUsageDescription': 'Oracle watches through your camera only when camera watch is started in the GUI.',
    },
)
