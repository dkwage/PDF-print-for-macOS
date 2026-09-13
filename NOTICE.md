# 저작권·배포 고지 / Attribution and distribution

PDFPrinter 0.2.0 — https://github.com/dkwage/PDF-print-for-macOS

기존 저장소의 기준 커밋은 `889abe8`이며 별도 LICENSE 파일은 없었습니다.
이 로컬 배포판은 기존 dkwage 프로젝트 코드와 이번 변경을 GNU AGPL v3 이상으로
제공합니다. 기존 저작자의 권리를 유지하며, 의존성에는 각각의 라이선스가 적용됩니다.
Copyright (c) dkwage and contributors. No warranty.

This local distribution of the original dkwage project and its modifications is
provided under GNU AGPL version 3 or later; see LICENSE. The baseline repository
(commit 889abe8) had no separate license file. No ownership of third-party work
is claimed. Changes add standalone packaging, bundled conversion, HTTP framing,
exclusive file creation, queue ownership checks, icons and integration checks.

## 포함 구성 요소 / Bundled components

- CPython 3.11.15, python-build-standalone runtime: PSF/Python licenses and runtime
  component notices in LICENSES/python-build-standalone. Same runtime build used
  by the local pdf2md reference (20260303 standalone distribution). Optional
  runtime notices are retained even when a module is not collected.
- rumps 0.4.0: BSD-3-Clause; Jared Suttles. LICENSES/rumps/LICENSE.
- ippserver 0.2: BSD-2-Clause; David Batley (h2g2bob), Alexander (devkral); copyright preserved
  verbatim in LICENSES/ippserver.txt. Runtime files are unmodified; our subclass
  handles HTTP framing, errors, saving and printer attributes.
- PyObjC core and Cocoa 12.2.1: MIT; Ronald Oussoren and contributors. Notices in
  LICENSES/pyobjc-core.txt and LICENSES/pyobjc-framework-Cocoa/.
- Ghostscript 10.07.1: Artifex Software, Inc. and contributors; GNU AGPL v3 or later,
  plus embedded component/font licenses and font embedding exception. LICENSES/
  Ghostscript.txt, LICENSE and LICENSES/ghostscript-components/ retain notices.
  The complete unmodified upstream source archive (including embedded libraries,
  fonts, ICC profiles and their notices) is included alongside source.zip in
  the release ZIP’s distribution/ folder. Build commands are in build_ghostscript.sh. No commercial license used.
- PyInstaller 6.21.0 bootloader: GPL v2 or later with the distribution exception
  retained in LICENSES/pyinstaller/COPYING.txt. Other build-tool licenses are
  included for attribution; those tools are not required on the recipient's Mac.

Ghostscript was compiled against its vendored libraries, with initialization data
and fonts compiled into the executable. It links only macOS libSystem and
libiconv. CUPS, AppKit, Foundation and system frameworks are provided by macOS,
not redistributed. requests and its dependencies are installed for upstream
package metadata but excluded from the app; the HTTP client is Python stdlib.

Official licensing sources:
- https://ghostscript.com/releases/gsdnld.html
- https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/tag/gs10071
- https://github.com/h2g2bob/ipp-server/blob/master/LICENSE
- https://github.com/ronaldoussoren/pyobjc/blob/v12.2.1/pyobjc-core/License.txt

## 소스와 재배포 / Source and redistribution

The release ZIP’s `distribution/` folder contains this notice, LICENSE,
LICENSES/, Korean/English documentation, source.zip (complete app/build/icon
sources), and ghostscript-10.07.1.tar.xz (complete corresponding Ghostscript
source). These files are outside the app to keep its installed size small.
Source and binary SHA-256 hashes are recorded in versions.json. Redistribute
these notices, source archives and build instructions together with the app.
Release downloads: https://github.com/dkwage/PDF-print-for-macOS/releases

## 아이콘 / Artwork

macos/AppIcon-original.png was generated using OpenAI image generation on
2026-09-13 for this project. No exclusive copyright claim is made over purely
AI-generated elements. macos/icon-prompt.txt records the prompt; the original
PNG, ICNS and AppKit menu-glyph generator are included in source.zip.
The menu glyph is original geometric artwork, drawn by macos/make_icons.py.
