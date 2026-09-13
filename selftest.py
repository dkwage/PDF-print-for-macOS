"""Runnable integration check; only temporary files and a unique CUPS queue."""
import concurrent.futures
import http.client
import io
import json
import pathlib
import socket
import subprocess
import tempfile
import time
import uuid
from ippserver.request import IppRequest
from ippserver.constants import SectionEnum as S, TagEnum as T, OperationEnum as O

PS = b'%!PS-Adobe-3.0\n/Helvetica findfont 24 scalefont setfont\n72 700 moveto (PDFPrinter integration test) show\nshowpage\n'


def run(app):
    checks = []
    from types import SimpleNamespace
    long_title = SimpleNamespace(_attributes={(S.operation, b'job-name', T.name_without_language): [('한' * 100).encode()]})
    assert len(app.job_title(long_title).encode()) <= 160
    checks.append('multibyte titles fit filesystem filename limit')
    original = app.OUT_DIR, app.PORT, app.PRINTER_QUEUE
    with tempfile.TemporaryDirectory(prefix='pdfprinter-test-') as temp:
        app.OUT_DIR = pathlib.Path(temp) / 'output'
        with socket.socket() as free:
            free.bind(('127.0.0.1', 0))
            app.PORT = free.getsockname()[1]
        app.PRINTER_QUEUE = 'pdfprinter_test_' + uuid.uuid4().hex[:10]
        service = app.PrinterService()
        app.notify = lambda *args: None
        app.PdfConvertPrinter.saved = lambda *args: None
        ps = pathlib.Path(temp) / 'input.ps'
        ps.write_bytes(PS)
        pdf = pathlib.Path(temp) / 'input.pdf'
        subprocess.run([app.GS, '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=pdfwrite', f'-sOutputFile={pdf}', str(ps)], check=True, timeout=120)
        source_pdf = pdf.read_bytes()

        def send(data, mime, chunked=False):
            attrs = {
                (S.operation, b'attributes-charset', T.charset): [b'utf-8'],
                (S.operation, b'attributes-natural-language', T.natural_language): [b'en'],
                (S.operation, b'printer-uri', T.uri): [f'ipp://127.0.0.1:{app.PORT}/ipp/print'.encode()],
                (S.operation, b'job-name', T.name_without_language): ['검증.report/../test'.encode()],
                (S.operation, b'document-format', T.mime_media_type): [mime],
            }
            payload = IppRequest((1, 1), O.print_job, 1, attrs).to_string() + data
            connection = http.client.HTTPConnection('127.0.0.1', app.PORT, timeout=150)
            connection.request('POST', '/ipp/print', [payload] if chunked else payload,
                               {'Content-Type': 'application/ipp'}, encode_chunked=chunked)
            response = connection.getresponse()
            assert response.status == 200, response.status
            result = IppRequest.from_file(io.BytesIO(response.read()))
            connection.close()
            return result.opid_or_status

        try:
            service.start()
            assert service.running and service.owns_queue
            checks.append('CUPS IPP Everywhere queue registration')
            assert send(source_pdf, b'application/pdf') == 0
            assert send(PS, b'application/postscript', True) == 0
            checks.append('IPP Content-Length PDF and chunked PostScript')
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                assert all(result == 0 for result in pool.map(lambda _: send(source_pdf, b'application/pdf'), range(4)))
            assert len(list(app.OUT_DIR.glob('*.pdf'))) == 6
            checks.append('concurrent same-title jobs preserved')
            assert any(p.read_bytes() == source_pdf for p in app.OUT_DIR.glob('*.pdf'))
            for file in app.OUT_DIR.glob('*.pdf'):
                subprocess.run([app.GS, '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=nullpage', str(file)], check=True, timeout=120)
                text = subprocess.check_output([app.GS, '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=txtwrite', '-sOutputFile=-', str(file)], timeout=120)
                assert b'PDFPrinter integration test' in text
            checks.append('all saved PDFs rendered and printed text preserved')
            assert send(b'%!PS\nthis_is_invalid\n', b'application/postscript') >= 0x500
            assert len(list(app.OUT_DIR.glob('*.ps'))) == 1
            assert send(b'unsupported', b'application/octet-stream') >= 0x500
            assert len(list(app.OUT_DIR.glob('*.bin'))) == 1
            checks.append('failed conversion/unsupported input return errors and retain originals')
            before = set(app.OUT_DIR.glob('*.pdf'))
            result = subprocess.run(['/usr/bin/lp', '-d', app.PRINTER_QUEUE, '-t', 'CUPS integration', str(pdf)], capture_output=True, text=True, check=True, timeout=30)
            deadline = time.monotonic() + 45
            while set(app.OUT_DIR.glob('*.pdf')) == before and time.monotonic() < deadline:
                time.sleep(0.2)
            added = set(app.OUT_DIR.glob('*.pdf')) - before
            assert len(added) == 1, result.stdout
            subprocess.run([app.GS, '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=nullpage', str(next(iter(added)))], check=True, timeout=120)
            checks.append('real macOS lp → CUPS → IPP → saved PDF')
            # Existing queues are refused without changing or deleting them.
            other = app.PrinterService()
            try:
                other._register_queue()
                raise AssertionError('existing queue was overwritten')
            except RuntimeError:
                pass
            other._unregister_queue()
            assert subprocess.run(['/usr/bin/lpstat', '-v', app.PRINTER_QUEUE], capture_output=True).returncode == 0
            checks.append('existing queue protected')
            service.stop()
            assert subprocess.run(['/usr/bin/lpstat', '-v', app.PRINTER_QUEUE], capture_output=True).returncode != 0
            service.start()
            service.stop()
            checks.append('stop, restart and owned-queue cleanup')
            # Explicit filename collision cannot overwrite a user's file.
            existing = pathlib.Path(temp) / 'existing.pdf'
            existing.write_bytes(b'keep')
            output = app.PdfConvertPrinter.publish(pdf, existing)
            assert existing.read_bytes() == b'keep' and output.read_bytes() == source_pdf
            checks.append('exclusive publish preserves existing files')
        finally:
            service.stop()
            app.OUT_DIR, app.PORT, app.PRINTER_QUEUE = original
    print(json.dumps({'result': 'PASS', 'checks': checks}, ensure_ascii=False, indent=2), flush=True)


def run_ui(app):
    import rumps
    with tempfile.TemporaryDirectory(prefix='pdfprinter-ui-') as temp:
        app.OUT_DIR = pathlib.Path(temp)
        app.PRINTER_QUEUE = 'pdfprinter_ui_' + uuid.uuid4().hex[:10]
        with socket.socket() as free:
            free.bind(('127.0.0.1', 0))
            app.PORT = free.getsockname()[1]
        menu = app.MenuBarApp()
        assert menu.service.running
        def finish(timer):
            timer.stop()
            assert menu.icon and menu.item_toggle.title == '프린터 정지'
            menu.on_toggle(None)
            assert not menu.service.running
            menu.on_toggle(None)
            assert menu.service.running
            print('PASS: native menu app, template icon, stop/start/quit', flush=True)
            menu.on_quit(None)
        rumps.Timer(finish, 5).start()
        menu.run()
