# PDFPrinter — virtual PDF printer for macOS

[한국어 README](README.md)

Choose **PDF Printer** in another app's print dialog to save a PDF in `~/PDFPrints`
and reveal it in Finder. The original menu bar interface is retained. Python and
Ghostscript are bundled: recipients need no Python, Homebrew, virtual environment
or internet connection.

## Install and use

1. Extract the release ZIP.
2. Move **PDFPrinter.app** to **Applications**.
3. Launch it and look for the printer icon in the menu bar.
4. In another app, press `⌘P`, select **PDF Printer**, and print.

This is a menu bar app: its Dock icon is deliberately hidden. Finder and Get Info
use the custom application icon. Documentation, notices and sources are in the ZIP’s separate `distribution/` folder.
Only the app is needed for installation; redistribute the complete ZIP including
`distribution/` when sharing with others.

- **프린터 정지 / 프린터 시작**: stop/start the server and its printer queue.
- **저장 폴더 열기**: open the output folder.
- **종료**: stop and remove only the queue created by this app run.
- **!** beside the icon means stopped; startup failures appear in a dialog.

Output filenames include the title, timestamp and unique suffix. Existing files
are never overwritten. PostScript is converted by bundled Ghostscript. Failed
conversion retains `.ps` and returns a printing error; unsupported data is
retained as `.bin`. Interrupted saves may leave `.incoming` files.

## Signing and Gatekeeper

This local release is **ad-hoc signed only**, **not Developer ID signed and not
Apple notarized**. Downloads may be blocked by Gatekeeper. If you trust the source,
try launching once, then use **System Settings → Privacy & Security → Open Anyway**.
Managed Macs may require an administrator. Do not disable system-wide security.

## Supported systems and limitations

- **Apple Silicon (arm64), macOS 14 Sonoma or later**. No Intel build is included.
- Tested on **macOS 26.6.2 / arm64**; macOS 14/15 and other physical Macs are untested.
- Requires a logged-in user and permission to manage CUPS printers. Restricted
  accounts may reject automatic queue registration. The app does not collect
  passwords or silently elevate privileges.
- Listens only on `127.0.0.1:6310`, while running. No login-item installation.
- PDF and PostScript, up to 512 MiB per job, 30-second socket read timeout and
  120-second PostScript conversion timeout. Intended for ordinary single-document
  printing; advanced job management, multi-document jobs and all IPP operations
  are not implemented.
- An existing `pdf_printer` queue is refused to protect its settings. Check in
  System Settings whether it is a stale queue from a previous run before manually
  removing it. Force quitting or system shutdown may leave a queue behind.
  Other printers and saved PDFs are not automatically removed.
- PostScript without embedded fonts may use bundled substitutes; review important
  documents. DRM, print restrictions and certificate security modules are not
  bypassed. The historical ICerti compatibility claim was not revalidated here.

## Build from source (developers only)

Requires an Apple Silicon Mac, Python 3.11, Xcode Command Line Tools
(`xcode-select --install`) and internet for initial dependencies. This release
uses python-build-standalone CPython 3.11.15.

```bash
bash build.sh
```

This creates a project-local `.build-venv`, installs pinned dependencies, verifies
the Ghostscript source SHA-256, builds it with vendored libraries and freezes the
runtime using PyInstaller. Existing build/dist directories are not wiped. A fresh
timestamped app, ZIP and SHA-256 file are produced under `packages/`. When building from bundled source.zip, place the
accompanying ghostscript-10.07.1.tar.xz in the extracted source's vendor/ directory
to skip that download.
Icons and their originals are in `macos/`; `macos/make_icons.py` regenerates PNG
sizes and the menu glyph. Existing ICNS is retained; remove that generated ICNS
explicitly if you want to regenerate it from changed artwork.

```bash
.build-venv/bin/python build_macos_app.py  # dependencies/Ghostscript already built
.build-venv/bin/python verify_distribution.py  # isolated app, denied dev paths, CUPS/UI
.build-venv/bin/python app.py             # source execution
.build-venv/bin/python app.py --self-test  # real CUPS, unique temporary queue/files
.build-venv/bin/python app.py --ui-smoke-test  # native menu, stop/start/quit
```

Builds receive an ad-hoc signature. Developer ID signing and notarization are
not automated. For a notarized release, sign nested binaries and the app using
Apple Developer credentials, submit using notarytool, staple, recreate the ZIP
and verify that separate release.

## License and source

This local distribution is **AGPL-3.0-or-later**. The baseline repository had no
separate license file; this distribution adds [LICENSE](LICENSE) and
[attribution/dependency notices](NOTICE.md). Ghostscript is used under AGPL,
without a commercial license.

The release ZIP’s `distribution/` includes complete app/build/icon sources in
source.zip, the complete Ghostscript source tarball, licenses, documentation and
hashes. Keep these together when redistributing. No GitHub publication was made.

## GitHub files

Commit source/build/check scripts, requirements, READMEs, LICENSE, NOTICE,
LICENSES/, icon originals/ICNS/menu PNG/generator in macos/, and vendor/ghostscript.sha256.
Attach the final ZIP and SHA-256 from packages/ to **GitHub Releases**, not Git.
Exclude virtual environments, build caches, old dist, downloaded Ghostscript source,
compiled Ghostscript, .DS_Store and generated iconsets. Commit the deletions of
previously tracked build/dist artifacts as part of this cleanup.
