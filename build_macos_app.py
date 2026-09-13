"""Build a slim standalone app; distribute notices and sources beside the app."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = '0.2.0'


def sha(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def main():
    if sys.platform != 'darwin' or platform.machine() != 'arm64':
        raise SystemExit('This release builder requires Apple Silicon macOS.')
    os.chdir(ROOT)
    gs = ROOT / 'ghostscript/gs'
    archive = ROOT / 'vendor/ghostscript-10.07.1.tar.xz'
    if not gs.is_file():
        raise SystemExit('Run bash build_ghostscript.sh first.')
    subprocess.run(['shasum', '-a', '256', '-c', 'vendor/ghostscript.sha256'], check=True)
    links = subprocess.check_output(['/usr/bin/otool', '-L', str(gs)], text=True)
    if any(not line.strip().startswith(('/usr/lib/', '/System/Library/')) for line in links.splitlines()[1:]):
        raise SystemExit('Ghostscript has non-system dependencies; rebuild using build_ghostscript.sh.')
    if not (ROOT / 'macos/MenuBar.png').is_file() or not (ROOT / 'macos/AppIcon.icns').is_file():
        subprocess.run([sys.executable, 'macos/make_icons.py'], check=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    name = f'PDFPrinter-{VERSION}-macos-arm64-{stamp}'
    stage = ROOT / 'build' / name
    output = ROOT / 'packages' / name
    stage.mkdir(parents=True)
    output.mkdir(parents=True)
    distribution = output / 'distribution'
    distribution.mkdir()
    for filename in ['README.md', 'README.en.md', 'NOTICE.md', 'LICENSE']:
        shutil.copy2(ROOT / filename, distribution / filename)
    shutil.copytree(ROOT / 'LICENSES', distribution / 'LICENSES')
    shutil.copy2(archive, distribution / archive.name)
    versions = {
        'app': VERSION, 'architecture': 'arm64', 'minimum_macos': '14.0',
        'build_macos': platform.mac_ver()[0], 'python': platform.python_version(),
        'dependencies': {n: importlib.metadata.version(n) for n in
                         ['rumps', 'ippserver', 'pyobjc-core', 'pyobjc-framework-Cocoa', 'pyinstaller']},
        'ghostscript': '10.07.1', 'ghostscript_source_sha256': sha(archive),
        'ghostscript_binary_sha256_before_signing': sha(gs),
        'ghostscript_source_url': 'https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10071/ghostscript-10.07.1.tar.xz',
        'signing': 'ad-hoc', 'developer_id': False, 'apple_notarization': False,
    }
    source = distribution / 'source.zip'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for name in ['app.py', 'selftest.py', 'build.sh', 'build_ghostscript.sh',
                     'build_macos_app.py', 'verify_distribution.py', 'PDFPrinter.spec', 'requirements.txt',
                     'requirements-build.txt', 'README.md', 'README.en.md', 'NOTICE.md',
                     'LICENSE', 'LICENSES', 'macos', '.gitignore', 'vendor/ghostscript.sha256']:
            path = ROOT / name
            for file in sorted(path.rglob('*')) if path.is_dir() else [path]:
                if file.is_file() and '__pycache__' not in file.parts and file.name != '.DS_Store' and not any(part.endswith('.iconset') for part in file.parts):
                    zipped.write(file, file.relative_to(ROOT))
    versions['app_source_sha256'] = sha(source)
    (distribution / 'versions.json').write_text(json.dumps(versions, indent=2) + '\n')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
                    '--distpath', str(stage / 'frozen'), '--workpath', str(stage / 'pyinstaller'),
                    str(ROOT / 'PDFPrinter.spec')], check=True,
                   env={**os.environ,
                        'PYINSTALLER_CONFIG_DIR': str(stage / 'pyinstaller-cache'),
                        'MACOSX_DEPLOYMENT_TARGET': '14.0'})
    app = output / 'PDFPrinter.app'
    shutil.copytree(stage / 'frozen/PDFPrinter.app', app, symlinks=True)
    subprocess.run(['/usr/bin/codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    for filename in ['README.md', 'README.en.md', 'NOTICE.md', 'LICENSE']:
        shutil.copy2(ROOT / filename, output / filename)
    package = output.with_name(output.name + '.zip')
    subprocess.run(['/usr/bin/ditto', '-c', '-k', '--keepParent', str(output), str(package)], check=True)
    package.with_suffix('.zip.sha256').write_text(f'{sha(package)}  {package.name}\n')
    (ROOT / 'build/latest-release.json').write_text(json.dumps({'app': str(app), 'zip': str(package)}, indent=2) + '\n')
    print(json.dumps({'app': str(app), 'zip': str(package)}, indent=2))


if __name__ == '__main__':
    main()
