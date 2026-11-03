"""Göçleri koşmak. Yalnızca geliştirme ve sınama içindir; üründe göçleri kurulum koşar (SPEC › 15)."""
from pathlib import Path

import psycopg

from .ayarlar import KOK, SEMA

GOCLER = KOK / 'veritabani'
GELISTIRME = KOK / 'gelistirme'


def goc_dosyalari():
    return sorted(GOCLER.glob('[0-9][0-9][0-9]_*.sql'))


def sema_sifirla(adres, ornek_ayarlar=True):
    """Şemayı silip açar; göçleri sırayla, sonra örnek firmanın ayarlarını koşar."""
    dosyalar = [GELISTIRME / 'sema_ac.sql', *goc_dosyalari()]
    if ornek_ayarlar:
        dosyalar.append(GELISTIRME / 'ornek_firma_ayarlari.sql')
    with psycopg.connect(adres, autocommit=False) as b:
        b.execute(f'DROP SCHEMA IF EXISTS {SEMA} CASCADE')
        for yol in dosyalar:
            b.execute(Path(yol).read_text('utf-8'))
    return dosyalar
