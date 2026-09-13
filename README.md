# PDF 프린터

[English README](README.en.md)

메뉴바 상주 가상 PDF 프린터. 인쇄하면 `~/PDFPrints`에 PDF 저장 후 Finder에 표시.
Python·Ghostscript 내장. 사용자에게 Python, Homebrew, 가상환경 설치 불필요.

## 동작 구조

```
앱(인쇄) → macOS CUPS → ipp://127.0.0.1:6310 (이 앱의 IPP 서버)
        → PDF면 그대로 저장 / PS면 내장 Ghostscript 변환 → Finder 표시
```

- 실행 시 `lpadmin`으로 "PDF Printer" 큐 자동 등록 (IPP Everywhere)
- 종료/정지 시 이번 실행에서 등록한 큐만 해제
- 127.0.0.1 바인딩. 앱 실행 중에만 인쇄 가능
- 같은 제목으로 인쇄해도 기존 파일을 덮어쓰지 않음
- PS 변환 실패 시 `.ps` 원본 보존. 미지원 데이터는 `.bin`으로 보존

## 설치·실행

1. 배포 ZIP 압축 해제
2. `PDFPrinter.app`을 응용 프로그램 폴더로 이동 후 실행
3. 다른 앱에서 `⌘P` → **PDF Printer** 선택 → 인쇄

메뉴바에 프린터 아이콘. 메뉴: 프린터 정지/시작, 저장 폴더 열기, 종료.
아이콘 옆 `!`는 정지 상태. Dock 아이콘은 표시하지 않음.

현재 배포본은 **ad-hoc 서명만 적용. Developer ID 서명·Apple 공증 없음.**
실행이 차단되면 출처를 확인한 뒤 시스템 설정 → 개인정보 보호 및 보안 → 확인 없이 열기.
조직 정책으로 차단된 경우 관리자 확인 필요.

## 지원 환경·제한

- Apple Silicon (arm64), macOS 14 Sonoma 이상. Intel 미지원
- 로그인된 사용자 세션과 CUPS 프린터 관리 권한 필요
- 기존 `pdf_printer` 큐가 있으면 덮어쓰지 않고 등록 중단. 이전 앱이 남긴 큐인지 확인 후 필요할 때만 직접 제거
- 강제 종료 시 큐가 남을 수 있음. 저장된 PDF는 자동 삭제하지 않음
- PDF·PostScript 단일 문서 인쇄용. 작업당 최대 512 MiB, 읽기 대기 30초, PS 변환 120초
- 글꼴이 포함되지 않은 PS는 대체 글꼴을 사용할 수 있음. DRM·보안 인쇄 제한 우회 기능 없음

## 검증된 프린트 환경

- macOS 26.6.2 / Apple Silicon: 실제 CUPS 인쇄, PDF 저장, PS 변환, 동시 인쇄, 정지/재시작 검증
- 앱만 임시 폴더로 복사하고 개발 소스·Python·Homebrew 경로를 차단한 상태에서 실행 검증
- macOS 14·15 및 다른 Mac은 실기 검증하지 않음
- 인하대학교 증명발급시스템(ICerti): 기존 버전 사용 사례. 이번 버전에서는 재검증하지 않음

## 소스 실행·빌드

개발자만 Python 3.11, Xcode Command Line Tools, 초기 다운로드용 인터넷 필요.

```bash
xcode-select --install  # Command Line Tools가 없는 경우
bash build.sh
```

`.build-venv`에 의존성 설치 → Ghostscript 소스·해시 확인 및 빌드 → PyInstaller로 앱 생성.
결과는 `packages/`의 `.app`, 배포 ZIP, SHA-256 파일.

```bash
.build-venv/bin/python app.py                       # 소스 실행 (빌드 준비 후)
.build-venv/bin/python app.py --self-test           # 임시 파일·고유 큐로 인쇄 검증
.build-venv/bin/python verify_distribution.py       # 최신 ZIP의 앱 격리·CUPS·메뉴 UI 검증
```

## 배포·라이선스

앱 약 **42.5 MiB**. 소스·라이선스는 앱 밖, 배포 ZIP의 `distribution/`에 포함.
설치는 앱만 이동. 재배포는 `distribution/`을 포함한 전체 ZIP 전달.

[AGPL-3.0-or-later](LICENSE). Ghostscript 원본 소스와 의존성 고지 포함. 상세 내용은 [NOTICE.md](NOTICE.md).
저장소에는 소스·빌드 파일·아이콘·라이선스만 관리. ZIP·SHA-256은 GitHub Releases 첨부용.
가상환경·빌드 캐시·바이너리·다운로드 원본은 Git에서 제외.

## 파일

| 파일 | 역할 |
| --- | --- |
| `app.py` | 메뉴바 앱 + IPP 서버 + 변환 + 큐 등록 |
| `build.sh` | 의존성 준비 → Ghostscript 빌드 → 앱·ZIP 생성 |
| `build_ghostscript.sh` | Ghostscript 소스 다운로드·해시 확인·빌드 |
| `build_macos_app.py`, `PDFPrinter.spec` | 런타임 포함 앱·배포 패키지 구성 |
| `requirements.txt`, `requirements-build.txt` | 실행·빌드 의존성 |
| `selftest.py`, `verify_distribution.py` | 실제 인쇄·독립 실행 검증 |
| `macos/` | 앱 아이콘 원본·ICNS·메뉴 아이콘·생성 스크립트 |
| `LICENSE`, `LICENSES/`, `NOTICE.md` | 프로젝트·의존성 라이선스 및 저작권 고지 |
