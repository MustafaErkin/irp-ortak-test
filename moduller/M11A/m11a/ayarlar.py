"""Ortam değişkenleri (SPEC › 4.3). IRP_* değişkenleri bağlantı katmanınındır; burada okunmaz."""
from dataclasses import dataclass
import os
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Ortam:
    veritabani: str
    test_veritabani: str
    kunye: Path
    gelistirme: bool
    kural_araligi_dk: int
    saglayici_m10: str | None


def ortam() -> Ortam:
    e = os.environ
    if not e.get('M11A_VERITABANI'):
        raise RuntimeError('Modül veritabanı açıkça ayarlanmalıdır.')
    return Ortam(
        veritabani=e['M11A_VERITABANI'],
        test_veritabani=e.get('M11A_TEST_VERITABANI', ''),
        kunye=Path(e.get('M11A_KUNYE') or KOK / 'kunye.json'),
        gelistirme=e.get('M11A_GELISTIRME') == '1',
        kural_araligi_dk=int(e.get('M11A_KURAL_ARALIGI_DK', '15')),
        saglayici_m10=(e.get('M11A_SAGLAYICI_M10') or '').strip() or None,
    )
