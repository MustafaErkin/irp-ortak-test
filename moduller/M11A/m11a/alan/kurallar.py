"""Kural işi: bildirimleri toparlar (SPEC › 8.7). Tekrar güvenlidir.

    python -m m11a.komutlar kurallari-calistir

Servis gözüyle yalnızca PROJE (aktif mi) okunur; para ve saat okunmaz. BUTCE_SAPMASI burada yeniden hesaplanmaz
(ölçüm kullanıcının gözüyledir); kural işi onu yalnızca kaldırır. Servis okuması gerçek bulutta MVP'den sonra gelir;
o zamana kadar 1. adım yalnızca simülatörde çalışır, öteki adımlar modülün tablosuna bakar."""
from collections import Counter
import logging

from ..baglanti import CekirdekHatasi
from ..depo import butce, projeler, ticari
from . import bildirim, eksik
from .tutar import tutar_degisti_birak

gunluk = logging.getLogger('m11a.kurallar')
KURALLAR = (bildirim.TICARI_DEVIR, bildirim.TUTAR_DEGISTI, bildirim.BUTCE_SAPMASI)


def calistir(cekirdek, b) -> dict:
    sayim = Counter()
    for p in projeler.acik_projeler(b):
        try:
            _proje(cekirdek, b, p, sayim)
        except CekirdekHatasi as h:
            gunluk.warning('%s için kural işi yarıda kaldı: %s', p['proje'], h)
            sayim['hata'] += 1
    return dict(sayim)


def _aktif(cekirdek, proje: str) -> bool | None:
    try:
        kayit = cekirdek.servis().oku('PROJE', proje).deger
    except CekirdekHatasi as h:
        gunluk.info('%s: servis okuması yok (%s); aktiflik denetlenmedi', proje, h.tur)
        return None
    return bool(kayit and kayit.get('aktif', True))


def _kaldir(cekirdek, b, proje: str, kurallar, sayim: Counter) -> None:
    for kural in kurallar:
        if bildirim.kaldir(cekirdek, b, proje, kural):
            sayim['kaldirilan'] += 1


def _proje(cekirdek, b, p: dict, sayim: Counter) -> None:
    proje = p['proje']
    if _aktif(cekirdek, proje) is False:                                   # 1
        _kaldir(cekirdek, b, proje, KURALLAR, sayim)
        return
    if p['butce_durumu'] == 'KAPALI':                                      # 2
        _kaldir(cekirdek, b, proje, (bildirim.BUTCE_SAPMASI, bildirim.TUTAR_DEGISTI), sayim)
    d = ticari.devir(b, proje)
    if d and d['durum'] == 'TAMAM':                                        # 3
        _kaldir(cekirdek, b, proje, (bildirim.TICARI_DEVIR,), sayim)
    elif d and (not d['bildirim_birakildi'] or d['son_suzulenler']):       # 4: erişim sonradan verilen muhasebeci
        if bildirim.ticari_devir_birak(cekirdek, b, p, eksik.acik_sayisi(ticari.eksikler(b, proje))):
            sayim['birakilan'] += 1
    son = (butce.tutar_degisiklikleri(b, proje) or [None])[-1]
    if son and not son['bildirim_birakildi'] and p['butce_durumu'] == 'ACIK':  # 5
        if tutar_degisti_birak(cekirdek, b, p, son):
            sayim['birakilan'] += 1


def hepsini_kaldir(cekirdek, b) -> int:
    """Modül kapatılırken: açık bildirimlerin hepsi kaldırılır."""
    n = 0
    for r in b.execute('SELECT proje, kural FROM mod_m11a.acik_bildirimler ORDER BY proje, kural').fetchall():
        n += bildirim.kaldir(cekirdek, b, r['proje'], r['kural'])
    return n
