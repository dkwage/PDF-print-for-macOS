# PDF 프린터

메뉴바 상주 가상 PDF 프린터. 인쇄하면 `~/PDFPrints`에 PDF 저장 후 Finder에 표시.

## 동작 구조

```
앱(인쇄) → macOS CUPS → ipp://127.0.0.1:6310 (이 앱의 IPP 서버)
        → PDF면 그대로 저장 / PS면 Ghostscript 변환 → Finder 표시
```

- 실행 시 `lpadmin`으로 "PDF Printer" 큐 자동 등록 (IPP Everywhere 시도, 실패 시 fallback)
- 종료/정지 시 큐 자동 해제
- 127.0.0.1 바인딩

## 필요 라이브러리

```bash
brew install ghostscript    # PS→PDF 변환용 (Mac이 PDF 직송하면 없어도 동작)
```

## 실행

```bash
pip3 install -r requirements.txt
python3 app.py
```

메뉴바에 🖨 아이콘. 메뉴: 프린터 정지/시작, 저장 폴더 열기, 종료.

## 검증된 프린트 환경

<li>
<ul> 인하대학교 증명발급시스템(ICerti)

## 파일

| 파일               | 역할                                       |
| ------------------ | ------------------------------------------ |
| `app.py`           | 메뉴바 앱 + IPP 서버 + 변환 + 큐 등록 전부 |
| `build.sh`         | PyInstaller → .app → pkgbuild              |
| `requirements.txt` | rumps, ippserver                           |
