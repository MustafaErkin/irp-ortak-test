"""Komutlar: python -m m10.komutlar <komut>

  gelistirme-vt-sifirla   Geliştirme veritabanında şemayı silip açar; göçleri ve örnek verileri koşar.
"""
import sys

import psycopg

from . import ayarlar


def sema_kur(adres, ornek=True):
    """Yalnızca yerelde: şemayı silip açar (gelistirme/sema_ac.sql), göçleri sırayla koşar, isterse örnek verileri.
    Üründe şemayı kurulum açar; göçleri biz koşarız."""
    dosyalar = [ayarlar.KOK / 'gelistirme' / 'sema_ac.sql', *sorted((ayarlar.KOK / 'veritabani').glob('*.sql'))]
    if ornek:
        dosyalar.append(ayarlar.KOK / 'gelistirme' / 'ornek_veriler.sql')
    with psycopg.connect(adres) as b:
        b.execute(f'DROP SCHEMA IF EXISTS {ayarlar.SEMA} CASCADE')
        for yol in dosyalar:
            b.execute(yol.read_text('utf-8'))


def main(arg):
    if arg[:1] == ['gelistirme-vt-sifirla']:
        sema_kur(ayarlar.veritabani())
        print(f'{ayarlar.SEMA} yeniden kuruldu: {ayarlar.veritabani()}')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
