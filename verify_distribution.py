"""Verify a copied app with development trees denied and a clean environment."""
import json
import argparse
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile
import zipfile

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--zip', type=Path, help='Release ZIP; defaults to newest packages/*.zip')
args = parser.parse_args()
package = args.zip or max((root / 'packages').glob('*.zip'), key=lambda p: p.stat().st_mtime)
report = root / 'packages/verification'
report.mkdir(exist_ok=True)
with zipfile.ZipFile(package) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert any('/distribution/source.zip' in name for name in names)
    assert any('/distribution/ghostscript-10.07.1.tar.xz' in name for name in names)
    assert not any('.app/Contents/Resources/distribution' in name for name in names)
extracted = tempfile.TemporaryDirectory(prefix='PDFPrinter ZIP ', dir='/private/tmp')
subprocess.run(['/usr/bin/ditto', '-x', '-k', str(package), extracted.name], check=True)
original = next(Path(extracted.name).glob('*/PDFPrinter.app'))
subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(original)], check=True)
with (original / 'Contents/Info.plist').open('rb') as file:
    info = plistlib.load(file)
assert info['LSUIElement'] and info['LSMinimumSystemVersion'] == '14.0'
assert (original / 'Contents/Resources/AppIcon.icns').is_file()
# All Mach-O dependencies must be system or bundle-relative; symlinks stay inside.
seen = set()
links = []
minimums = set()
for file in original.rglob('*'):
    if file.is_symlink():
        assert file.resolve().is_relative_to(original.resolve()), file
    if not file.is_file() or file.resolve() in seen:
        continue
    seen.add(file.resolve())
    with file.open('rb') as stream:
        magic = stream.read(4)
    if magic not in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xfe\xed\xfa\xcf'):
        continue
    output = subprocess.check_output(['/usr/bin/otool', '-L', str(file)], text=True)
    for line in output.splitlines()[1:]:
        dependency = line.strip().split(' (', 1)[0]
        assert dependency.startswith(('/usr/lib/', '/System/Library/', '@')), (file, dependency)
    load = subprocess.check_output(['/usr/bin/otool', '-l', str(file)], text=True)
    load = '\n'.join(load.splitlines()[1:])
    assert '/opt/homebrew' not in load and '/Users/' not in load, file
    for minimum in re.findall(r'\bminos\s+(\S+)', load):
        assert tuple(map(int, minimum.split('.'))) <= (14, 0, 0), (file, minimum)
        minimums.add(minimum)
    links.append(output)
(report / 'mach-o-dependencies.txt').write_text('\n'.join(links))
with tempfile.TemporaryDirectory(prefix='PDFPrinter isolated ', dir='/private/tmp') as temp:
    temp = Path(temp)
    app = temp / 'PDFPrinter.app'
    shutil.copytree(original, app, symlinks=True)
    (temp / 'home').mkdir()
    (temp / 'tmp').mkdir()
    # Deny original sources, both development Python runtimes and Homebrew reads.
    blocked = [str(root.parent), str(Path.home() / '.local/share/uv'),
               str(Path.home() / '.pyenv'), '/opt/homebrew', '/usr/local']
    policy = temp / 'isolation.sb'
    policy.write_text('(version 1)\n(allow default)\n' + '\n'.join(
        '(deny file-read* (subpath ' + json.dumps(path) + '))' for path in blocked))
    environment = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(temp / 'home'),
                   'TMPDIR': str(temp / 'tmp'), 'LANG': 'en_US.UTF-8'}
    executable = app / 'Contents/MacOS/PDFPrinter'
    for mode in ['--self-test', '--ui-smoke-test']:
        result = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(policy), str(executable), mode],
                                cwd=temp, env=environment, capture_output=True, text=True, timeout=240)
        (report / f'{mode[2:]}.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0 and 'PASS' in result.stdout, (mode, result.stdout, result.stderr)
    # Demonstrate the policy really denies the source directory.
    probe = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(policy), '/bin/cat', str(root / 'app.py')],
                           capture_output=True, env=environment)
    assert probe.returncode != 0
summary = {'result': 'PASS', 'app': 'PDFPrinter.app (extracted from ZIP)', 'zip': str(package),
           'external_sources_and_licenses': True,
           'isolated_copy': True, 'clean_environment': True,
           'source_python_homebrew_reads_denied': True,
           'real_cups_and_conversion': True, 'native_menu_smoke': True,
           'macho_minimum_versions': sorted(minimums),
           'signature': 'ad-hoc; codesign --verify --deep --strict passed',
           'developer_id': False, 'notarized': False}
(report / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
extracted.cleanup()
print(json.dumps(summary, indent=2))
