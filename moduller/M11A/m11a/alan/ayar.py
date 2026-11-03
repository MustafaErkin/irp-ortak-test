"""Ayarlar (SPEC › 8.9): kalıplar, sapma eşiği, yaklaşan tarih günü, yedek saat ücretleri. Yalnızca YETKILI."""
from decimal import Decimal

from ..api.hatalar import dogrulama
from ..depo import ayarlar as depo
from . import kod, yetki
from .butce import metin

PROJE_KODU_DEGISKENLERI = frozenset({'YY', 'YYYY', 'AA', 'SIRA3'})


def _cevap(i) -> dict:
    a = depo.oku(i.b)
    return i.cevap({**a, 'degiskenler': sorted(kod.DEGISKENLER),
                    'saat_ucretleri': [{'birim': u['birim'], 'ucret': metin(u['ucret']), 'para_birimi': u['para_birimi']}
                                       for u in depo.saat_ucretleri(i.b)]})


def oku(i) -> dict:
    i.rol_gerek(yetki.AYARLAR)
    return _cevap(i)


def yaz(i, g) -> dict:
    i.rol_gerek(yetki.AYARLAR)
    hatalar = []
    for alan, izinli in (('proje_kodu_deseni', PROJE_KODU_DEGISKENLERI), ('siparis_adi_deseni', kod.DEGISKENLER)):
        desen = getattr(g, alan)
        bilinmeyen = sorted(kod.kalip_degiskenleri(desen) - izinli)
        if bilinmeyen:
            hatalar.append({'alan': alan, 'sira': None, 'mesaj': 'Bilinmeyen değişken: ' + ', '.join(bilinmeyen)})
    if 'SIRA3' not in kod.kalip_degiskenleri(g.proje_kodu_deseni):
        hatalar.append({'alan': 'proje_kodu_deseni', 'sira': None, 'mesaj': 'Proje kodu {SIRA3} taşımalı.'})
    elif not kod.elle_kod_gecerli(kod.proje_kodu(g.proje_kodu_deseni, _ornek_tarih(), 1)):
        hatalar.append({'alan': 'proje_kodu_deseni', 'sira': None,
                        'mesaj': 'Üretilen kod 2–20 harf, rakam ya da tire olmalı.'})
    birimler = {b['kimlik'] for b in i.oku('BIRIMLER') or []}
    for n, u in enumerate(g.saat_ucretleri, 1):
        if u.birim not in birimler:
            hatalar.append({'alan': 'saat_ucretleri.birim', 'sira': n, 'mesaj': f'{u.birim} çekirdekte birim değil.'})
    if len({u.birim for u in g.saat_ucretleri}) != len(g.saat_ucretleri):
        hatalar.append({'alan': 'saat_ucretleri.birim', 'sira': None, 'mesaj': 'Bir birim bir kez yazılır.'})
    if hatalar:
        raise dogrulama(hatalar)
    an = i.simdi()
    with i.b.transaction():
        depo.yaz(i.b, {'proje_kodu_deseni': g.proje_kodu_deseni, 'proje_kodu_sira_kapsami': g.proje_kodu_sira_kapsami,
                       'siparis_adi_deseni': g.siparis_adi_deseni,
                       'sapma_esigi_puan': _sayi(g.sapma_esigi_puan), 'yaklasan_tarih_gun': g.yaklasan_tarih_gun},
                 i.kisi, an)
        depo.saat_ucretlerini_yaz(i.b, [u.model_dump() for u in g.saat_ucretleri], i.kisi, an)
    return _cevap(i)


def _ornek_tarih():
    from datetime import date
    return date(2026, 11, 2)


def _sayi(x: Decimal):
    return int(x) if x == x.to_integral_value() else float(x)
