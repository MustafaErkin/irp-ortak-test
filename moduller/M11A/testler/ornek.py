"""Sınamanın ortak örneği: Ek D.5 (testler/sabitler/M10.KAZANAN_SURUM.json), küçük gerçek bir PDF'le."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path

SABIT = Path(__file__).resolve().parent / 'sabitler' / 'M10.KAZANAN_SURUM.json'


def kucuk_pdf(metin: str = 'T-2026-0012/V2') -> bytes:
    """Tek sayfalık, geçerli bir PDF (çapraz başvuru tablosu baytlarıyla)."""
    akis = f'BT /F1 18 Tf 72 720 Td ({metin}) Tj ET'.encode()
    nesneler = [b'<< /Type /Catalog /Pages 2 0 R >>',
                b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R '
                b'/Resources << /Font << /F1 5 0 R >> >> >>',
                b'<< /Length %d >>\nstream\n' % len(akis) + akis + b'\nendstream',
                b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    cikti, yerler = bytearray(b'%PDF-1.4\n'), []
    for n, govde in enumerate(nesneler, 1):
        yerler.append(len(cikti))
        cikti += b'%d 0 obj\n' % n + govde + b'\nendobj\n'
    xref = len(cikti)
    cikti += b'xref\n0 %d\n0000000000 65535 f \n' % (len(nesneler) + 1)
    cikti += b''.join(b'%010d 00000 n \n' % y for y in yerler)
    cikti += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(nesneler) + 1, xref)
    return bytes(cikti)


def kazanan_surum(**degisiklik) -> dict:
    s = json.loads(SABIT.read_text('utf-8'))
    pdf = kucuk_pdf(degisiklik.get('etiket', s['etiket']))
    s['pdf'] = dict(s['pdf'], icerik_base64=base64.b64encode(pdf).decode(), parmak_izi=hashlib.sha256(pdf).hexdigest())
    s.update(deepcopy(degisiklik))
    return s


def ek_is(surum: int, bagli_proje: str, **degisiklik) -> dict:
    """Kaynağı EK_IS olan, kimliği değişmiş kopya (M11A08)."""
    return kazanan_surum(surum=surum, etiket=f'T-2026-00{surum}/V1', talep=surum, talep_no=f'T-2026-00{surum}',
                         kaynak='EK_IS', bagli_proje=bagli_proje, konu=f'Ek iş {surum}', **degisiklik)
