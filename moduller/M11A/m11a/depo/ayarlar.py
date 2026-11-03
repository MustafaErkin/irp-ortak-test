"""Ayarlar ve yedek saat ücretleri (mod_m11a.ayarlar, mod_m11a.saat_ucretleri)."""
from decimal import Decimal

from psycopg.types.json import Jsonb

VARSAYILAN = {
    'proje_kodu_deseni': '{YY}{AA}{SIRA3}',
    'proje_kodu_sira_kapsami': 'YIL',
    'siparis_adi_deseni': '{YYYY}-{YILLIK_SIRA3}-{PROJE_KODU}___{MUSTERI}-{PROJE_ADI}_{PO}',
    'sapma_esigi_puan': 15,
    'yaklasan_tarih_gun': 30,
}


def oku(b) -> dict:
    a = dict(VARSAYILAN)
    a.update({r['anahtar']: r['deger'] for r in b.execute('SELECT anahtar, deger FROM mod_m11a.ayarlar')})
    return a


def yaz(b, degerler: dict, kim: str, an: str) -> None:
    for anahtar, deger in degerler.items():
        b.execute("""INSERT INTO mod_m11a.ayarlar (anahtar, deger, guncelleyen, guncelleme_ani) VALUES (%s, %s, %s, %s)
                     ON CONFLICT (anahtar) DO UPDATE SET deger = EXCLUDED.deger, guncelleyen = EXCLUDED.guncelleyen,
                       guncelleme_ani = EXCLUDED.guncelleme_ani""", (anahtar, Jsonb(deger), kim, an))


def saat_ucretleri(b) -> list[dict]:
    return b.execute('SELECT birim, ucret, para_birimi FROM mod_m11a.saat_ucretleri ORDER BY birim').fetchall()


def saat_ucretlerini_yaz(b, satirlar: list[dict], kim: str, an: str) -> None:
    b.execute('DELETE FROM mod_m11a.saat_ucretleri')
    for s in satirlar:
        b.execute("""INSERT INTO mod_m11a.saat_ucretleri (birim, ucret, para_birimi, guncelleyen, guncelleme_ani)
                     VALUES (%s, %s, %s, %s, %s)""", (s['birim'], Decimal(str(s['ucret'])), s['para_birimi'], kim, an))
