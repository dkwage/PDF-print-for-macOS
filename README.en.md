# PDF Printer

[한국어 README](README.md)

Menu bar virtual PDF printer. Saves print jobs to `~/PDFPrints` and reveals them in Finder.
Python and Ghostscript included. No Python, Homebrew or virtual environment installation needed.

## How it works

```
App (print) → macOS CUPS → ipp://127.0.0.1:6310 (this app's IPP server)
            → save PDF / convert PS with bundled Ghostscript → reveal in Finder
```

- Registers the "PDF Printer" queue through `lpadmin` on launch (IPP Everywhere)
- Removes only the queue created by this run on stop/quit
- Binds to 127.0.0.1. Printing available only while the app is running
- Repeated job titles do not overwrite existing files
- Failed PS conversion retains the `.ps` original. Unsupported data retained as `.bin`

## Install and run

1. Extract the release ZIP
2. Move `PDFPrinter.app` to Applications and launch
3. In another app, press `⌘P` → select **PDF Printer** → print

Printer icon in the menu bar. Menu: stop/start printer, open output folder, quit.
Menu labels are in Korean. `!` beside the icon means stopped. No Dock icon.

Current build: **ad-hoc signed only. No Developer ID signature or Apple notarization.**
If blocked, verify the source, then use System Settings → Privacy & Security → Open Anyway.
Contact your administrator if blocked by organization policy.

## Supported systems and limitations

- Apple Silicon (arm64), macOS 14 Sonoma or later. No Intel support
- Requires a logged-in user session and permission to manage CUPS printers
- Refuses registration if `pdf_printer` already exists. Check whether it is a stale queue from an earlier run before manually removing it
- Force quitting may leave the queue behind. Saved PDFs are not automatically deleted
- Single-document PDF/PostScript printing. Maximum 512 MiB per job, 30-second read timeout, 120-second PS conversion timeout
- PS without embedded fonts may use substitutes. No DRM or secure-print restriction bypass

## Verified printing environments

- macOS 26.6.2 / Apple Silicon: real CUPS printing, PDF saving, PS conversion, concurrent jobs, stop/restart
- App copied alone to a temporary folder, with development source, Python and Homebrew paths blocked
- macOS 14/15 and other Macs have not been tested on hardware
- Inha University certificate service (ICerti): reported use with the previous version. Not revalidated with this version

## Run and build from source

Developers only: Python 3.11, Xcode Command Line Tools and internet for initial downloads.

```bash
xcode-select --install  # If Command Line Tools are missing
bash build.sh
```

Install dependencies in `.build-venv` → download, verify and build Ghostscript → freeze the app with PyInstaller.
Outputs: `.app`, release ZIP and SHA-256 file under `packages/`.

```bash
.build-venv/bin/python app.py                       # Run source after build setup
.build-venv/bin/python app.py --self-test           # Print checks with temporary files/unique queue
.build-venv/bin/python verify_distribution.py       # Latest ZIP: isolated app, CUPS and menu UI checks
```

## Distribution and license

App size: approximately **42.5 MiB**. Sources and licenses are outside the app, in the release ZIP's `distribution/` folder.
Move only the app to install. Share the complete ZIP, including `distribution/`, when redistributing.

[AGPL-3.0-or-later](LICENSE). Includes Ghostscript source and dependency notices. See [NOTICE.md](NOTICE.md).
Track only source, build files, icons and licenses in Git. ZIP/SHA-256 files are GitHub Releases attachments.
Virtual environments, build caches, binaries and downloaded source archives are excluded from Git.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Menu bar app + IPP server + conversion + queue registration |
| `build.sh` | Prepare dependencies → build Ghostscript → create app/ZIP |
| `build_ghostscript.sh` | Download, verify and build Ghostscript source |
| `build_macos_app.py`, `PDFPrinter.spec` | Bundle runtime and assemble release package |
| `requirements.txt`, `requirements-build.txt` | Runtime/build dependencies |
| `selftest.py`, `verify_distribution.py` | Real printing and standalone execution checks |
| `macos/` | Original app icon, ICNS, menu icon and generation script |
| `LICENSE`, `LICENSES/`, `NOTICE.md` | Project/dependency licenses and copyright notices |
