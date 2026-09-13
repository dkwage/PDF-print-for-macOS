# PDFPrinter — macOS 가상 PDF 프린터

[English README](README.en.md)

다른 앱의 인쇄 창에서 **PDF Printer**를 선택하면 `~/PDFPrints`에 PDF를
저장하고 Finder에서 표시합니다. 기존 메뉴 막대 UI를 유지합니다.
Python·Ghostscript 런타임이 앱에 포함되어 있어 사용자에게 Python, Homebrew,
가상환경 설치가 필요하지 않습니다. 인터넷 연결도 필요하지 않습니다.

## 설치·실행

1. 배포 ZIP을 압축 해제합니다.
2. **PDFPrinter.app만 응용 프로그램(`/Applications`) 폴더로 옮깁니다.**
3. 앱을 실행하면 메뉴 막대에 프린터 아이콘이 나타납니다.
4. 다른 앱에서 `⌘P` → **PDF Printer** → 인쇄합니다.

메뉴 막대 전용 앱이므로 실행 중 Dock 아이콘은 의도적으로 숨깁니다.
Finder와 앱 정보에는 전용 PDF 프린터 아이콘이 표시됩니다.
앱에는 실행에 필요한 파일만 포함합니다. 문서·라이선스·소스는 ZIP의 별도 `distribution/` 폴더에 있습니다.
설치는 앱만 옮기면 됩니다. 다른 사람에게 재배포할 때는 `distribution/`을 포함한 전체 ZIP을 전달하세요.

### 서명과 Gatekeeper

현재 로컬 배포본은 **ad-hoc 서명만 적용**했습니다. **Developer ID 개발자 서명 및
Apple 공증은 되어 있지 않습니다.** 따라서 인터넷으로 받은 앱은 Gatekeeper에 의해
차단될 수 있습니다. 출처를 신뢰한다면 실행을 한 번 시도한 뒤 **시스템 설정 →
개인정보 보호 및 보안 → 확인 없이 열기**에서 허용합니다. 조직 정책으로 이 기능이
차단된 Mac에서는 관리자에게 문의해야 합니다. 시스템 보안 기능을 전체 해제할 필요는 없습니다.

## 사용법

- **프린터 정지 / 프린터 시작**: IPP 서버와 이 실행에서 만든 프린터 큐를 정지·재등록합니다.
- **저장 폴더 열기**: `~/PDFPrints`를 Finder에서 엽니다.
- **종료**: 서버를 종료하고 이 실행에서 등록한 큐만 제거합니다.
- 파일명은 작업 제목·날짜·고유 문자열로 구성됩니다. 기존 파일은 덮어쓰지 않습니다.
- PostScript는 포함된 Ghostscript로 변환합니다. 변환 실패 시 원본 `.ps`를 보존하며
  인쇄 오류를 반환합니다. 미지원 데이터는 `.bin`, 중단된 저장은 `.incoming`으로 남을 수 있습니다.
- 프린터 아이콘 옆 **!**는 서버가 정지된 상태입니다. 시작 실패 이유는 대화상자로 표시됩니다.

## 지원 환경·제한

- 이 배포본: **Apple Silicon (arm64), macOS 14 Sonoma 이상**. Intel용 앱은 포함하지 않습니다.
- 실제 실행·인쇄 검증: **macOS 26.6.2 / arm64**. macOS 14·15 및 다른 Mac의 실기 검증은 하지 않았습니다.
- 로그인된 사용자 세션과 macOS CUPS 프린터 관리 권한이 필요합니다. 관리형/제한 계정에서는
  큐 자동 등록이 거부될 수 있습니다. 앱은 암호를 수집하거나 자동으로 관리자 권한을 요청하지 않습니다.
- 로컬 `127.0.0.1:6310`만 수신합니다. 앱 실행 중에만 사용할 수 있고 자동 로그인 실행은 설정하지 않습니다.
- 지원 형식: PDF, PostScript. 작업당 최대 512 MiB, 읽기 대기 30초, PS 변환 120초.
  일반 단일 문서 인쇄용이며 고급 인쇄 작업 관리·여러 문서 묶음·모든 IPP 기능을 구현하지 않습니다.
- 기존 `pdf_printer` 큐가 있으면 설정 보호를 위해 등록을 중단합니다. 시스템 설정의 프린터 목록에서
  해당 큐가 이전 PDFPrinter가 남긴 큐인지 직접 확인하고 필요할 때만 제거한 뒤 다시 시작하세요.
  강제 종료·시스템 종료 후에도 큐가 남을 수 있습니다. 다른 프린터나 저장 PDF는 자동 삭제하지 않습니다.
- 글꼴이 포함되지 않은 PS는 내장 대체 글꼴을 사용할 수 있습니다. 중요한 문서는 출력물을 확인하세요.
- 복사/인쇄 방지, DRM, 증명서 보안 모듈을 우회하지 않습니다. 기존 README에 기재된 ICerti 사용 사례는
  이번 배포본에서 재검증하지 않았으며 모든 사이트·프로그램과의 호환성을 보장하지 않습니다.

## 소스 실행·빌드 (개발자만)

수신자에게는 아래 도구가 필요하지 않습니다. 개발자는 Apple Silicon Mac, Python 3.11,
Xcode Command Line Tools(`xcode-select --install`), 초기 의존성 다운로드용 인터넷이 필요합니다.
이 릴리스는 python-build-standalone CPython 3.11.15로 빌드했습니다.

```bash
bash build.sh
```

스크립트는 프로젝트 전용 `.build-venv`를 만들고 고정된 의존성을 설치합니다.
Ghostscript 공식 소스를 SHA-256 확인 후 로컬에서 빌드하고 PyInstaller로 런타임을 묶습니다.
아이콘 원본·ICNS는 `macos/`에 있으며 `macos/make_icons.py`로 크기별 PNG와 메뉴 아이콘을 재생성합니다.
기존 build/dist 전체를 삭제하지 않고 타임스탬프가 있는 별도 경로에 생성합니다.
결과 앱·ZIP·SHA-256 파일 위치는 완료 시 출력됩니다.
배포 ZIP의 `distribution/source.zip`을 풀어 빌드할 때는 함께 제공된 `ghostscript-10.07.1.tar.xz`를
풀어낸 소스의 `vendor/` 폴더에 넣으면 Ghostscript 다운로드를 생략할 수 있습니다.

```bash
# 빌드된 앱 재생성 (의존성·Ghostscript 준비 후)
.build-venv/bin/python build_macos_app.py
# 소스 실행
.build-venv/bin/python app.py
# 최신 빌드 앱을 임시 폴더로 복사하고 개발 경로 차단·CUPS·UI 검증
.build-venv/bin/python verify_distribution.py
# 실제 CUPS 통합 검증: 임시 파일과 고유 테스트 큐만 사용
.build-venv/bin/python app.py --self-test
# 네이티브 메뉴 UI 시작·정지·재시작·종료 검증
.build-venv/bin/python app.py --ui-smoke-test
```

빌드 스크립트는 ad-hoc 서명을 합니다. Developer ID 서명·공증은 자동 실행하지 않습니다.
공식 외부 배포가 필요하면 Apple Developer 자격으로 포함 실행 파일부터 앱까지 서명하고,
`notarytool` 제출·`stapler` 처리 후 ZIP을 다시 만들어 별도 검증해야 합니다.

## 라이선스·포함 소스

이 로컬 배포판은 **AGPL-3.0-or-later**로 제공합니다. 기준 저장소에는 별도 LICENSE가 없었으며,
이번 배포에 [LICENSE](LICENSE)와 [저작권·의존성 고지](NOTICE.md)를 추가했습니다.
Ghostscript도 AGPL로 포함하며 상용 라이선스는 사용하지 않습니다.

배포 ZIP의 `distribution/`에 앱 전체 소스 ZIP, Ghostscript 원본 소스,
빌드 스크립트, 의존성 라이선스와 해시가 들어 있습니다. 재배포할 때 함께 유지하세요.

## GitHub에 올릴 파일

저장소에는 앱 소스, 빌드·검증 스크립트, requirements 파일, README·LICENSE·NOTICE,
`LICENSES/`, `macos/`의 아이콘 원본·ICNS·메뉴 PNG·생성 스크립트, `vendor/ghostscript.sha256`을 올립니다.
`packages/`의 최종 ZIP과 SHA-256은 **GitHub Releases 첨부용**이며 Git에 커밋하지 않습니다.
가상환경, 빌드 캐시, 과거 dist, Ghostscript 바이너리·다운로드 원본, `.DS_Store`, 생성된 iconset은 제외합니다.
기존 Git에 추적되던 build/dist 파일은 이번 정리의 삭제 변경으로 반영해야 합니다.
