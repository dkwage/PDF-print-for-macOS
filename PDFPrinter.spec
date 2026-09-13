# Build with build_macos_app.py; all paths are relative to the source or staging area.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files
root = Path(SPECPATH)
a = Analysis(
    [str(root / 'app.py')], pathex=[str(root)],
    binaries=[(str(root / 'ghostscript/gs'), 'ghostscript')],
    datas=[(str(root / 'macos/MenuBar.png'), 'macos')] + collect_data_files('ippserver'),
    hiddenimports=['selftest'],
    excludes=['requests', 'certifi', 'charset_normalizer', 'urllib3', 'idna', 'tkinter', 'pip', 'setuptools'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PDFPrinter',
          console=False, argv_emulation=False, target_arch='arm64', codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, name='PDFPrinter')
app = BUNDLE(coll, name='PDFPrinter.app', icon=str(root / 'macos/AppIcon.icns'),
             bundle_identifier='io.github.dkwage.pdfprinter',
             info_plist={'CFBundleShortVersionString': '0.2.0', 'CFBundleVersion': '0.2.0',
                         'LSUIElement': True, 'LSMinimumSystemVersion': '14.0',
                         'NSHighResolutionCapable': True})
