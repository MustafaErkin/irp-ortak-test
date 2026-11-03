"""Modülün kimliği ve ortam değişkenleri (SPEC › 3, 4.3).

Kod değişince yalnızca buradaki KOD ve SEMA, künye ve göçlerdeki şema adı değişir.
IRP_* değişkenleri bağlantı katmanınındır; burada okunmaz.
"""
import os
from pathlib import Path

KOD = 'M10'
SEMA = 'mod_m10'
KOK = Path(__file__).resolve().parents[1]


def kunye_yolu():
    return Path(os.environ.get('M10_KUNYE') or KOK / 'kunye.json')


def veritabani():
    if not os.environ.get('M10_VERITABANI'):
        raise RuntimeError('Modül veritabanı açıkça ayarlanmalıdır.')
    return os.environ['M10_VERITABANI']


def test_veritabani():
    if not os.environ.get('M10_TEST_VERITABANI'):
        raise RuntimeError('Ayrı test veritabanı açıkça ayarlanmalıdır.')
    return os.environ['M10_TEST_VERITABANI']


def gelistirme():
    """Geliştirme girişi yalnızca M10_GELISTIRME=1 iken açıktır; üründe yoktur."""
    return os.environ.get('M10_GELISTIRME') == '1'
