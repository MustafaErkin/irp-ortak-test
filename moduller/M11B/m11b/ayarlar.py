"""Ortam değişkenleri ve modülün kimlik sabitleri.

Modül kodu ve şema adı yalnızca burada yazılır (SPEC › 3). Kod değişince künye, göçlerdeki şema adı ve bu dosya değişir.
IRP_CEKIRDEK, IRP_TABAN, IRP_ANON, IRP_SERVIS burada okunmaz; onları bağlantı katmanı okur.
"""
from dataclasses import dataclass
import os
from pathlib import Path

KOD = 'M11B'
SEMA = f'mod_{KOD.lower()}'

KOK = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Ayarlar:
    veritabani: str
    kunye: Path
    kural_araligi_dk: int
    klasor_ayraci: str
    gelistirme: bool

    @classmethod
    def ortamdan(cls, veritabani=None):
        return cls(
            veritabani=veritabani or os.environ['M11B_VERITABANI'],
            kunye=Path(os.environ.get('M11B_KUNYE', KOK / 'kunye.json')),
            kural_araligi_dk=int(os.environ.get('M11B_KURAL_ARALIGI_DK', '15')),
            klasor_ayraci=os.environ.get('M11B_KLASOR_AYRACI', '_'),
            gelistirme=os.environ.get('M11B_GELISTIRME') == '1',
        )


def test_veritabani():
    return os.environ['M11B_TEST_VERITABANI']
