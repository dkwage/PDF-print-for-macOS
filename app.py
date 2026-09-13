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
import os
import sys
import logging
import uuid
import subprocess
import tempfile
import threading

import struct

import rumps
from ippserver.server import IPPServer, IPPRequestHandler
from ippserver.behaviour import SaveFilePrinter
from ippserver.constants import SectionEnum, TagEnum, StatusCodeEnum
from ippserver.request import IppRequest

APP_NAME = "PDFPrinter"
PRINTER_QUEUE = "pdf_printer"        # lpadmin 큐 이름 (공백 불가)
PRINTER_DESC = "PDF Printer"      # 프린터 설명 (공백 가능)
PORT = 6310
OUT_DIR = pathlib.Path("~/PDFPrints").expanduser()


# ---------- 유틸 ----------

RESOURCE_DIR = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))


def find_gs():
    bundled = RESOURCE_DIR / "ghostscript" / "gs"
    if bundled.is_file():
        return str(bundled)
    if not getattr(sys, "frozen", False):
        return shutil.which("gs")
    raise RuntimeError("앱에 포함된 Ghostscript가 없습니다. 앱을 다시 설치하세요.")


GS = find_gs()


def job_title(ipp_request):
    try:
        for (_, name, _), values in ipp_request._attributes.items():
            if name in (b"job-name", b"document-name") and values:
                t = values[0].decode("utf-8", "replace")
                t = re.sub(r'[/\\:*?"<>|\x00-\x1f\x7f]', "_", t).strip(' .')
                if t:
                    return t.encode("utf-8")[:160].decode("utf-8", "ignore")
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_uri = f"ipp://127.0.0.1:{PORT}/".encode()
        self.printer_uri = self.base_uri + b"ipp/print"

    def printer_list_attributes(self):
        attr = super().printer_list_attributes()
        attr.update(everywhere_attributes(PORT))
        return attr

    def handle_postscript(self, ipp_request, postscript_file):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        title = job_title(ipp_request) or "print-job"
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        # mkstemp reserves the filename atomically, including concurrent jobs.
        fd, name = tempfile.mkstemp(prefix=f"{title}-{ts}-", suffix=".incoming", dir=OUT_DIR)
        path = pathlib.Path(name)
        with os.fdopen(fd, "wb") as output:
            shutil.copyfileobj(postscript_file, output)
        self.run_after_saving(path, ipp_request)

    def run_after_saving(self, filename, ipp_request):
        path = pathlib.Path(filename)
        with path.open("rb") as source:
            head = source.read(8)
        if head.startswith(b"%PDF-"):
            suffix = ".pdf"
        elif head.startswith(b"%!PS"):
            try:
                if not GS:
                    raise RuntimeError("Ghostscript를 찾을 수 없습니다")
                with tempfile.TemporaryDirectory(prefix="pdfprinter-") as work:
                    converted = pathlib.Path(work) / "converted.pdf"
                    result = subprocess.run(
                        [GS, "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
                         "-sDEVICE=pdfwrite", f"-sOutputFile={converted}", str(path)],
                        capture_output=True, timeout=120,
                        env={k: v for k, v in os.environ.items()
                             if not k.startswith(("GS_", "DYLD_"))},
                    )
                    if result.returncode or not converted.is_file():
                        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-1000:])
                    with converted.open("rb") as check:
                        if not check.read(5) == b"%PDF-":
                            raise RuntimeError("PDF 변환 결과가 올바르지 않습니다")
                    # Publish exclusively; preserve the incoming original on failure.
                    destination = self.publish(converted, path.with_suffix(".pdf"))
                path.unlink()
                self.saved(destination)
                return
            except Exception as error:
                destination = self.publish(path, path.with_suffix(".ps"))
                path.unlink()
                notify("변환 실패", f"PostScript 원본 보존: {destination.name}")
                raise RuntimeError(f"PostScript 변환 실패: {error}") from error
        else:
            destination = self.publish(path, path.with_suffix(".bin"))
            path.unlink()
            raise ValueError(f"지원하지 않는 인쇄 데이터. 원본 보존: {destination.name}")
        destination = self.publish(path, path.with_suffix(suffix))
        path.unlink()
        self.saved(destination)

    @staticmethod
    def publish(source, destination):
        while True:
            try:
                output = destination.open("xb")
                break
            except FileExistsError:
                destination = destination.with_name(f"{destination.stem}-{uuid.uuid4().hex[:8]}{destination.suffix}")
        with output, source.open("rb") as incoming:
            shutil.copyfileobj(incoming, output)
        return destination

    def saved(self, path):
        notify("PDF 저장 완료", path.name)
        try:
            subprocess.run(["/usr/bin/open", "-R", str(path)], timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            logging.exception("Finder 표시 실패; PDF는 저장되었습니다")


class RequestHandler(IPPRequestHandler):
    """Bound HTTP bodies: upstream 0.2 otherwise waits for EOF on keep-alive jobs."""
    def parse_request(self):
        from http.server import BaseHTTPRequestHandler
        result = BaseHTTPRequestHandler.parse_request(self)
        self.close_connection = True
        self.connection.settimeout(30)
        return result

    def handle_expect_100(self):
        self.send_response_only(100)
        self.end_headers()
        return True

    def handle_ipp(self):
        try:
            with tempfile.TemporaryFile() as body:
                total = 0
                chunked = self.headers.get("Transfer-Encoding", "").lower() == "chunked"
                remaining = int(self.headers.get("Content-Length", "0"))
                if not chunked and remaining <= 0:
                    raise ValueError("Content-Length required")
                while True:
                    count = int(self.rfile.readline(128).split(b";", 1)[0], 16) if chunked else remaining
                    if count < 0 or total + count > 512 * 1024 * 1024:
                        raise ValueError("Job exceeds 512 MiB")
                    if not count:
                        break
                    total += count
                    while count:
                        block = self.rfile.read(min(count, 65536))
                        if not block:
                            raise ValueError("Incomplete job")
                        body.write(block)
                        count -= len(block)
                    if not chunked:
                        break
                    if self.rfile.read(2) != b"\r\n":
                        raise ValueError("Invalid chunk")
                body.seek(0)
                request = IppRequest.from_file(body)
                try:
                    response = self.server.behaviour.handle_ipp(request, body)
                except Exception:
                    logging.exception("인쇄 작업 실패")
                    response = IppRequest((1, 1), StatusCodeEnum.server_error_internal_error,
                                          request.request_id, self.server.behaviour.minimal_attributes())
                data = response.to_string()
            self.send_headers(200, "application/ipp", len(data))
            self.wfile.write(data)
        except (ValueError, OSError, EOFError) as error:
            self.send_error(400, str(error))


# ---------- 서버 + 큐 등록 ----------

class PrinterService:
    def __init__(self):
        self.server = None
        self.thread = None
        self.owns_queue = False

    @property
    def running(self):
        return self.server is not None

    def start(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        behaviour = PdfConvertPrinter(directory=str(OUT_DIR), filename_ext="pdf")
        self.server = IPPServer(("127.0.0.1", PORT), RequestHandler, behaviour)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"[+] IPP: ipp://127.0.0.1:{PORT}/ipp/print")
        print(f"[+] 저장 폴더: {OUT_DIR}")
        try:
            self._register_queue()
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self._unregister_queue()

    def _register_queue(self):
        uri = f"ipp://127.0.0.1:{PORT}/ipp/print"
        existing = subprocess.run(["/usr/bin/lpstat", "-v", PRINTER_QUEUE],
                                  capture_output=True, text=True, timeout=15)
        if existing.returncode == 0:
            raise RuntimeError(f"기존 '{PRINTER_QUEUE}' 큐가 있습니다. 기존 설정 보호를 위해 등록을 중단했습니다.")
        result = subprocess.run(
            ["/usr/sbin/lpadmin", "-p", PRINTER_QUEUE, "-E", "-v", uri,
             "-m", "everywhere", "-D", PRINTER_DESC, "-o", "printer-is-shared=false"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode:
            raise RuntimeError("프린터 등록 실패 (프린터 관리 권한을 확인하세요): " + result.stderr.strip())
        self.owns_queue = True
        notify("프린터 연결됨", f"'{PRINTER_DESC}' 사용 가능")

    def _unregister_queue(self):
        if not self.owns_queue:
            return
        current = subprocess.run(["/usr/bin/lpstat", "-v", PRINTER_QUEUE],
                                 capture_output=True, text=True, timeout=15)
        if current.returncode == 0 and current.stdout.strip().endswith(f"ipp://127.0.0.1:{PORT}/ipp/print"):
            result = subprocess.run(["/usr/sbin/lpadmin", "-x", PRINTER_QUEUE],
                                    capture_output=True, timeout=15)
            if result.returncode:
                notify("큐 정리 실패", "시스템 설정에서 PDF Printer를 확인하세요.")
        self.owns_queue = False


# ---------- 메뉴바 ----------

class MenuBarApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title="", icon=str(RESOURCE_DIR / "macos/MenuBar.png"),
                         template=True, quit_button=None)
        self.service = PrinterService()
        self.item_toggle = rumps.MenuItem("프린터 정지", callback=self.on_toggle)
        self.item_folder = rumps.MenuItem("저장 폴더 열기", callback=self.on_folder)
        self.item_quit = rumps.MenuItem("종료", callback=self.on_quit)
        self.menu = [self.item_toggle, self.item_folder, None, self.item_quit]
        self.start_service()

    def start_service(self):
        try:
            self.service.start()
        except Exception as error:
            rumps.alert(APP_NAME, str(error))
        self.title = "" if self.service.running else "!"
        self.item_toggle.title = "프린터 정지" if self.service.running else "프린터 시작"

    def on_toggle(self, _):
        if self.service.running:
            self.service.stop()
            self.title = "!"
            self.item_toggle.title = "프린터 시작"
        else:
            self.start_service()

    def on_folder(self, _):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["/usr/bin/open", str(OUT_DIR)])

    def on_quit(self, _):
        self.service.stop()
        rumps.quit_application()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from selftest import run
        run(sys.modules[__name__])
    elif "--ui-smoke-test" in sys.argv:
        from selftest import run_ui
        run_ui(sys.modules[__name__])
    else:
        MenuBarApp().run()
