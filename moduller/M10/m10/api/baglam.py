"""İsteğin bağlamı: kullanıcının oturumu ve kişisi.

Ekran kullanıcının erişim anahtarını `Authorization: Bearer` ile iletir; arka yüz `cekirdek.oturum(anahtar)`
ile çalışır (07_on_yuz.md › 2). Kişi istek başına bir kez KISILER'den okunur (SPEC › 5).
"""
from fastapi import Depends, Header

from irp_sozlesme.baglanti import CekirdekHatasi

from .. import baglanti, hatalar, vt
from ..alan.yetki import Kisi, kisi_kur
from ..depo import ayarlar as ayar_deposu

ERISIM_YOK = "M1.0'a erişiminiz yok. Teklifleri satış yöneticisi, yetkili ve yönetim görür."


class Baglam:
    def __init__(self, oturum, kisi: Kisi, kisiler):
        self.oturum, self.kisi, self.kisiler = oturum, kisi, kisiler
        self.hesaplaniyor = False
        self._birimler = None

    def oku(self, veri, hedef=None, **g):
        """Kullanıcının gözüyle okur; okuma güncel değilse cevaba "hesaplaniyor" eklenir."""
        okuma = self.oturum.oku(veri, hedef, **g)
        if not okuma.guncel:
            self.hesaplaniyor = True
        return okuma.deger

    def birimler(self):
        """Çekirdeğin BIRIMLER'i, istek başına bir kez."""
        if self._birimler is None:
            self._birimler = self.oku('BIRIMLER') or []
        return self._birimler

    def birim_denetle(self, kodlar, alan='birim'):
        """İşçilik, başlangıç tablosu, saat ücreti ve etap birimi çekirdeğin listesinden olmalı (Ek D.2)."""
        bilinen = {x['kimlik'] for x in self.birimler()}
        yanlis = [hatalar.hata(alan, f'{k} çekirdeğin birim listesinde yok.', i)
                  for i, k in enumerate(kodlar, 1) if k and k not in bilinen]
        if yanlis:
            raise hatalar.dogrulama(yanlis)

    def kisi_adi(self, kimlik):
        return next((k.get('ad') for k in self.kisiler if k.get('kimlik') == kimlik), None) if kimlik else None


def _anahtar(authorization):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise hatalar.oturum_yok()
    return authorization[7:].strip()


def baglam(authorization: str | None = Header(default=None)) -> Baglam:
    anahtar = _anahtar(authorization)
    try:
        oturum = baglanti.oturum(anahtar)
    except CekirdekHatasi as e:
        if e.tur == 'YETKI':
            raise hatalar.oturum_yok() from None
        raise
    okuma = oturum.oku('KISILER')
    kisiler = okuma.deger or []
    kayit = next((k for k in kisiler if k.get('kimlik') == oturum.kisi), None)
    if kayit is None:
        raise hatalar.yetki('Kişi kaydınız bulunamadı.')
    with vt.islem() as b:
        yonetim_birimleri = ayar_deposu.oku(b, 'yonetim_birimleri', [])
    bg = Baglam(oturum, kisi_kur(kayit, yonetim_birimleri), kisiler)
    bg.hesaplaniyor = not okuma.guncel
    return bg


def erisimli(bg: Baglam = Depends(baglam)) -> Baglam:
    """M1.0'a erişimi olmayanın her isteği 403 alır (SPEC › 6)."""
    if not bg.kisi.erisim:
        raise hatalar.yetki(ERISIM_YOK)
    return bg


def duzenleyici(bg: Baglam = Depends(erisimli)) -> Baglam:
    if not bg.kisi.duzenleyici:
        raise hatalar.yetki()
    return bg


def onayci(bg: Baglam = Depends(erisimli)) -> Baglam:
    if not bg.kisi.onayci:
        raise hatalar.yetki('Bu işi yalnızca onaycı (yetkili) yapar.')
    return bg
