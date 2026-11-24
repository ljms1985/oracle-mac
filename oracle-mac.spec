# PyInstaller spec for Oracle for macOS — INTEL (x86_64) build.
#
# INTEL ONLY — target_arch='x86_64'. Built on a GitHub-hosted
# macos-15-intel runner (native Intel Mac in the cloud). Do NOT build
# this spec on an Apple Silicon runner: PyInstaller cannot cross-build
# an x86_64 binary from an arm64 Python interpreter. The arm64 build
# lives in ~/workspace/oracle-mac/ (oracle-mac.spec, target_arch='arm64').
# See INTEL_BUILD_NOTES.md for the full investigation.
# Output: dist/Oracle.app  (Intel only — will not run on Apple Silicon
# via Rosetta in reverse; an arm64 Mac runs it via Rosetta 2, an Intel
# Mac runs it natively.)
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
        'PIL', 'PIL.Image', 'PIL.ImageTk',
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
    target_arch='x86_64',
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
        'LSMinimumSystemVersion': '10.13',
        'NSMicrophoneUsageDescription': 'Oracle listens for your voice when always-listening is turned on in the GUI.',
        'NSCameraUsageDescription': 'Oracle watches through your camera only when camera watch is started in the GUI.',
    },
)
