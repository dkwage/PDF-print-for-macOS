#!/usr/bin/env python3
"""
모두의 프린터 for Mac — 메뉴바 앱.

기능:
- IPP 가상 프린터 서버 (PDF/PS 수신, PS는 Ghostscript로 PDF 변환)
- 실행 시 lpadmin으로 Mac에 프린터 자동 등록, 종료 시 해제
- 저장 후 Finder에서 파일 자동 표시
- 메뉴바에서 시작/정지/종료
"""
import datetime
import pathlib
import re
import shutil
import socket
import subprocess
import tempfile
import threading

import struct

import rumps
from ippserver.server import IPPServer, IPPRequestHandler
from ippserver.behaviour import SaveFilePrinter
from ippserver.constants import SectionEnum, TagEnum

APP_NAME = "PDFPrinter"
PRINTER_QUEUE = "pdf_printer"        # lpadmin 큐 이름 (공백 불가)
PRINTER_DESC = "PDF Printer"      # 프린터 설명 (공백 가능)
PORT = 6310
OUT_DIR = pathlib.Path("~/PDFPrints").expanduser()


# ---------- 유틸 ----------

def find_gs():
    for p in ("gs", "/opt/homebrew/bin/gs", "/usr/local/bin/gs"):
        w = shutil.which(p)
        if w:
            return w
    return None


GS = find_gs()


def job_title(ipp_request):
    try:
        for (_, name, _), values in ipp_request._attributes.items():
            if name in (b"job-name", b"document-name") and values:
                t = values[0].decode("utf-8", "replace")
                t = re.sub(r'[/\\:*?"<>|]', "_", t).strip()
                if t:
                    return t[:80]
    except Exception:
        pass
    return None


def notify(title, message):
    try:
        rumps.notification(APP_NAME, title, message)
    except Exception:
        pass


# ---------- IPP Everywhere 속성 ----------
# lpadmin -m everywhere 는 Get-Printer-Attributes 응답으로 PPD를 생성한다.
# 아래 속성 없으면 "Unable to create PPD: Printer does not support required
# IPP attributes or document formats." 로 실패.

_P = SectionEnum.printer

def _kw(name, *vals):
    return {(_P, name.encode(), TagEnum.keyword): [v.encode() for v in vals]}

def _enum(name, *vals):
    return {(_P, name.encode(), TagEnum.enum): [struct.pack(">i", v) for v in vals]}

def _bool(name, val):
    return {(_P, name.encode(), TagEnum.boolean): [struct.pack(">b", 1 if val else 0)]}

def _int(name, *vals):
    return {(_P, name.encode(), TagEnum.integer): [struct.pack(">i", v) for v in vals]}

def _rng(name, lo, hi):
    return {(_P, name.encode(), TagEnum.range_of_integer): [struct.pack(">ii", lo, hi)]}

def _res(name, *vals):
    return {(_P, name.encode(), TagEnum.resolution): [struct.pack(">iib", x, y, 3) for x, y in vals]}

def _uri(name, *vals):
    return {(_P, name.encode(), TagEnum.uri): [v.encode() for v in vals]}

MEDIA = ["iso_a4_210x297mm", "na_letter_8.5x11in", "iso_a3_297x420mm",
         "iso_a5_148x210mm", "iso_b5_176x250mm", "na_legal_8.5x14in"]


def everywhere_attributes(port):
    e = {}
    e.update(_uri("printer-uri-supported", f"ipp://127.0.0.1:{port}/ipp/print"))
    e.update(_kw("uri-security-supported", "none"))
    e.update(_kw("uri-authentication-supported", "none"))
    e.update(_kw("ipp-versions-supported", "1.1", "2.0"))
    e.update(_kw("ipp-features-supported", "ipp-everywhere"))
    e.update({(_P, b"printer-name", TagEnum.name_without_language): [PRINTER_QUEUE.encode()]})
    e.update(_kw("media-default", MEDIA[0]))
    e.update(_kw("media-supported", *MEDIA))
    e.update(_kw("media-type-supported", "stationery"))
    e.update(_kw("media-source-supported", "auto"))
    for side in ("bottom", "top", "left", "right"):
        e.update(_int(f"media-{side}-margin-supported", 0))
    e.update(_res("printer-resolution-default", (600, 600)))
    e.update(_res("printer-resolution-supported", (300, 300), (600, 600)))
    e.update(_kw("sides-default", "one-sided"))
    e.update(_kw("sides-supported", "one-sided"))
    e.update(_bool("color-supported", True))
    e.update(_kw("print-color-mode-default", "auto"))
    e.update(_kw("print-color-mode-supported", "auto", "color", "monochrome"))
    e.update(_enum("print-quality-default", 4))
    e.update(_enum("print-quality-supported", 3, 4, 5))
    e.update(_enum("finishings-default", 3))
    e.update(_enum("finishings-supported", 3))
    e.update(_int("copies-default", 1))
    e.update(_rng("copies-supported", 1, 1))
    e.update(_enum("orientation-requested-default", 3))
    e.update(_enum("orientation-requested-supported", 3, 4))
    e.update(_kw("output-bin-default", "face-down"))
    e.update(_kw("output-bin-supported", "face-down"))
    e.update({(_P, b"document-format-supported", TagEnum.mime_media_type):
              [b"application/pdf", b"application/postscript", b"application/octet-stream"]})
    return e


# ---------- 프린터 동작 ----------

class PdfConvertPrinter(SaveFilePrinter):
    def printer_list_attributes(self):
        attr = super().printer_list_attributes()
        attr.update(everywhere_attributes(PORT))
        return attr

    def filename(self, ipp_request):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        title = job_title(ipp_request) or "print-job"
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        base = OUT_DIR / f"{title}-{ts}"
        p, n = base.with_suffix(".pdf"), 1
        while p.exists():
            p = base.with_name(f"{base.name}-{n}").with_suffix(".pdf")
            n += 1
        return str(p)

    def run_after_saving(self, filename, ipp_request):
        path = pathlib.Path(filename)
        with open(path, "rb") as f:
            head = f.read(8)

        if head.startswith(b"%!PS"):
            if GS:
                tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                tmp.close()
                r = subprocess.run(
                    [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
                     "-sDEVICE=pdfwrite", f"-sOutputFile={tmp.name}", str(path)],
                    capture_output=True,
                )
                if r.returncode == 0:
                    shutil.move(tmp.name, path)
                else:
                    pathlib.Path(tmp.name).unlink(missing_ok=True)
                    notify("변환 실패", "PostScript 원본으로 저장됨")
            else:
                notify("Ghostscript 없음", "PS 원본 저장. brew install ghostscript")

        notify("PDF 저장 완료", path.name)
        subprocess.run(["open", "-R", str(path)])   # Finder에서 표시


# ---------- 서버 + 큐 등록 ----------

class PrinterService:
    def __init__(self):
        self.server = None
        self.thread = None

    @property
    def running(self):
        return self.server is not None

    def start(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        behaviour = PdfConvertPrinter(directory=str(OUT_DIR), filename_ext="pdf")
        self.server = IPPServer(("127.0.0.1", PORT), IPPRequestHandler, behaviour)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"[+] IPP: ipp://127.0.0.1:{PORT}/ipp/print")
        print(f"[+] 저장 폴더: {OUT_DIR}")
        self._register_queue()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self._unregister_queue()

    def _register_queue(self):
        uri = f"ipp://127.0.0.1:{PORT}/ipp/print"
        # 1차: IPP Everywhere (Mac이 PDF 직송)
        r = subprocess.run(
            ["lpadmin", "-p", PRINTER_QUEUE, "-E", "-v", uri,
             "-m", "everywhere", "-D", PRINTER_DESC,
             "-o", "printer-is-shared=false"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            # 2차: 모델 미지정 fallback (PS로 와도 서버가 변환)
            r = subprocess.run(
                ["lpadmin", "-p", PRINTER_QUEUE, "-E", "-v", uri,
                 "-D", PRINTER_DESC, "-o", "printer-is-shared=false"],
                capture_output=True, text=True,
            )
        if r.returncode == 0:
            subprocess.run(["cupsenable", PRINTER_QUEUE], capture_output=True)
            subprocess.run(["cupsaccept", PRINTER_QUEUE], capture_output=True)
            print(f"[+] 프린터 등록됨: {PRINTER_QUEUE}")
            notify("프린터 연결됨", f"'{PRINTER_DESC}' 사용 가능")
        else:
            print(f"[!] lpadmin 실패: {r.stderr.strip()}")
            notify("프린터 등록 실패", r.stderr.strip()[:100] or "lpadmin 오류")

    def _unregister_queue(self):
        subprocess.run(["lpadmin", "-x", PRINTER_QUEUE], capture_output=True)


# ---------- 메뉴바 ----------

class MenuBarApp(rumps.App):
    def __init__(self):
        super().__init__("🖨", quit_button=None)
        self.service = PrinterService()
        self.item_toggle = rumps.MenuItem("프린터 정지", callback=self.on_toggle)
        self.item_folder = rumps.MenuItem("저장 폴더 열기", callback=self.on_folder)
        self.item_quit = rumps.MenuItem("종료", callback=self.on_quit)
        self.menu = [self.item_toggle, self.item_folder, None, self.item_quit]
        self.service.start()

    def on_toggle(self, _):
        if self.service.running:
            self.service.stop()
            self.title = "🖨✕"
            self.item_toggle.title = "프린터 시작"
        else:
            self.service.start()
            self.title = "🖨"
            self.item_toggle.title = "프린터 정지"

    def on_folder(self, _):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(OUT_DIR)])

    def on_quit(self, _):
        self.service.stop()
        rumps.quit_application()


if __name__ == "__main__":
    MenuBarApp().run()
