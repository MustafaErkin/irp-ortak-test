"""ayarlar tablosu: anahtar–değer (jsonb)."""
from psycopg.types.json import Jsonb


def oku(b, anahtar, varsayilan=None):
    satir = b.execute('SELECT deger FROM ayarlar WHERE anahtar = %s', (anahtar,)).fetchone()
    return varsayilan if satir is None else satir['deger']


def hepsi(b):
    return {s['anahtar']: s['deger'] for s in b.execute('SELECT anahtar, deger FROM ayarlar ORDER BY anahtar')}


def yaz(b, anahtar, deger, kim, an):
    b.execute('INSERT INTO ayarlar (anahtar, deger, guncelleyen, guncelleme_ani) VALUES (%s, %s, %s, %s) '
              'ON CONFLICT (anahtar) DO UPDATE SET deger = EXCLUDED.deger, guncelleyen = EXCLUDED.guncelleyen, '
              'guncelleme_ani = EXCLUDED.guncelleme_ani', (anahtar, Jsonb(deger), kim, an))
