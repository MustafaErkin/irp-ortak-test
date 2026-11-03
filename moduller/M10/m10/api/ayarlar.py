"""Ayarlar ve geçmiş proje formu (SPEC › 8.14). Tek ekran, iki sekme.

Kim: SATIS, YETKILI, yönetim birimleri; yonetim_birimleri'ni yalnızca YETKILI değiştirir.
"""
from fastapi import APIRouter, Depends, Query

from .. import baglanti, hatalar, vt
from ..alan.arama import eslesir, kod_uret
from ..depo import ayarlar as ayar_deposu
from ..depo import gecmis as gecmis_deposu
from ..depo import katalog as kd
from .baglam import Baglam, duzenleyici, erisimli
from .semalar import (BaslangicSatiri, GecmisProje, GenelAyarlar, KatalogKalemi, MakineTuru, SablonSatiri, SaatUcreti,
                      Unsur, YeniUnsur)
from .yanit import yanit

yol = APIRouter()


def _ayarlayabilir(bg: Baglam = Depends(erisimli)) -> Baglam:
    if not bg.kisi.ayarlayabilir:
        raise hatalar.yetki('Ayarları satış yöneticisi, yetkili ve yönetim değiştirir.')
    return bg


def _para_denetle(b, kodlar, alan='para_birimi'):
    bilinen = {p['kod'] for p in kd.para_birimleri(b)}
    yanlis = [hatalar.hata(alan, f'{k} tanımlı bir para birimi değil.', i)
              for i, k in enumerate(kodlar, 1) if k and k not in bilinen]
    if yanlis:
        raise hatalar.dogrulama(yanlis)


# ---------------------------------------------------------------- maliyet unsurları

@yol.get('/ayarlar/unsurlar')
def unsurlar(bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'unsurlar': kd.unsurlar(b)})


@yol.put('/ayarlar/unsurlar')
def unsurlari_kaydet(govde: list[Unsur], bg: Baglam = Depends(_ayarlayabilir)):
    """Kullanılmış unsurun bütçe kalemi değişirse uyarı: gönderilmiş sürümler onaydaki özetle kalır."""
    an = baglanti.simdi()
    uyarilar = []
    with vt.islem() as b:
        eski = {u['kod']: u for u in kd.unsurlar(b)}
        kullanilmis = kd.kullanilmis_unsurlar(b, [u.kod for u in govde])
        for u in govde:
            d = u.model_dump()
            if u.kod in eski:
                if eski[u.kod]['butce_kalemi'] != u.butce_kalemi and u.kod in kullanilmis:
                    uyarilar.append(hatalar.hata('butce_kalemi', f'{u.ad}: Gönderilmiş sürümler eski kalemle kaldı.'))
                kd.unsur_guncelle(b, d)
            else:
                kd.unsur_ekle(b, d, bg.kisi.kimlik, an)
        return yanit({'unsurlar': kd.unsurlar(b), 'uyarilar': uyarilar})


@yol.post('/unsurlar', status_code=201)
def diger_unsur(govde: YeniUnsur, bg: Baglam = Depends(duzenleyici)):
    """"Diğer…": ad ve bütçe kalemi zorunlu; kod addan üretilir. Yeni unsur sonraki teklifte hazır gelir."""
    with vt.islem() as b:
        kod = kod_uret(govde.ad, [u['kod'] for u in kd.unsurlar(b)])
        kd.unsur_ekle(b, {'kod': kod, 'ad': govde.ad, 'butce_kalemi': govde.butce_kalemi, 'sik': govde.sik},
                      bg.kisi.kimlik, baglanti.simdi())
        return yanit(kd.unsur(b, kod), 201)


# ---------------------------------------------------------------- kalem kataloğu

@yol.get('/ayarlar/katalog')
def katalog_ayari(bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'kalemler': kd.katalog(b)})


@yol.put('/ayarlar/katalog')
def katalogu_kaydet(govde: list[KatalogKalemi], bg: Baglam = Depends(_ayarlayabilir)):
    with vt.islem() as b:
        _para_denetle(b, [k.para_birimi for k in govde])
        for i, k in enumerate(govde, 1):
            if (k.birim_fiyat is None) != (k.para_birimi is None):
                raise hatalar.dogrulama([hatalar.hata('birim_fiyat', 'Fiyat ve para birimi birlikte girilir.', i)])
            if kd.katalog_kodu_var(b, k.kod, k.kimlik):
                raise hatalar.dogrulama([hatalar.hata('kod', f'{k.kod} kodu başka bir kalemde var.', i)])
            if k.kimlik:
                if not kd.katalog_guncelle(b, k.kimlik, k.model_dump()):
                    raise hatalar.bulunamadi(f'Katalog kalemi {k.kimlik} yok.')
            else:
                kd.katalog_ekle(b, k.model_dump())
        return yanit({'kalemler': kd.katalog(b)})


@yol.get('/katalog')
def katalog_ara(q: str = '', bg: Baglam = Depends(erisimli)):
    """Teklif formu için: aktif kalemler, kod, ad ve unsur adında VE araması."""
    with vt.islem() as b:
        kalemler = [k for k in kd.katalog(b, yalniz_aktif=True)
                    if eslesir(q, ' '.join(filter(None, (k['kod'], k['ad'], k['unsur_adi']))))]
        return yanit({'kalemler': kalemler})


# ---------------------------------------------------------------- makine türleri ve başlangıç tablosu

@yol.get('/ayarlar/makine-turleri')
def makine_turleri(bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'makine_turleri': kd.makine_turleri(b)})


@yol.put('/ayarlar/makine-turleri')
def makine_turlerini_kaydet(govde: list[MakineTuru], bg: Baglam = Depends(_ayarlayabilir)):
    with vt.islem() as b:
        for m in govde:
            kd.makine_turu_kaydet(b, m.model_dump())
        return yanit({'makine_turleri': kd.makine_turleri(b)})


@yol.get('/ayarlar/baslangic-tablosu')
def baslangic_tablosu(makine_turu: str | None = Query(default=None), bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'satirlar': kd.baslangic_tablosu(b, makine_turu)})


@yol.put('/ayarlar/baslangic-tablosu')
def baslangic_tablosunu_kaydet(govde: list[BaslangicSatiri], bg: Baglam = Depends(_ayarlayabilir)):
    bg.birim_denetle([s.birim for s in govde])
    with vt.islem() as b:
        turler = {m['kod'] for m in kd.makine_turleri(b)}
        yanlis = [hatalar.hata('makine_turu', f'{s.makine_turu} tanımlı değil.', i)
                  for i, s in enumerate(govde, 1) if s.makine_turu not in turler]
        if yanlis:
            raise hatalar.dogrulama(yanlis)
        kd.baslangic_tablosu_yaz(b, [s.model_dump() for s in govde])
        return yanit({'satirlar': kd.baslangic_tablosu(b)})


# ---------------------------------------------------------------- saat ücretleri

@yol.get('/ayarlar/saat-ucretleri')
def saat_ucretleri(bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'ucretler': kd.saat_ucretleri(b)})


@yol.put('/ayarlar/saat-ucretleri')
def saat_ucretlerini_kaydet(govde: list[SaatUcreti], bg: Baglam = Depends(_ayarlayabilir)):
    """Teklifin saat ücreti modülün varsayımıdır; çekirdeğin maaşı ya da saat maliyeti değildir (karar 104)."""
    bg.birim_denetle([s.birim for s in govde])
    with vt.islem() as b:
        _para_denetle(b, [s.para_birimi for s in govde])
        kd.saat_ucretleri_yaz(b, [s.model_dump() for s in govde], bg.kisi.kimlik, baglanti.simdi())
        return yanit({'ucretler': kd.saat_ucretleri(b)})


# ---------------------------------------------------------------- takvim şablonu

@yol.get('/ayarlar/takvim-sablonu')
def takvim_sablonu(bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'satirlar': kd.takvim_sablonu(b)})


@yol.put('/ayarlar/takvim-sablonu')
def takvim_sablonunu_kaydet(govde: list[SablonSatiri], bg: Baglam = Depends(_ayarlayabilir)):
    """Yalnızca satırların birimi ve aktifliği değişir; kod, ad, sıra, oran M1.1B ile ortaktır."""
    bg.birim_denetle([s.birim for s in govde])
    with vt.islem() as b:
        for i, s in enumerate(govde, 1):
            if not kd.sablon_guncelle(b, s.kod, s.birim, s.aktif):
                raise hatalar.dogrulama([hatalar.hata('kod', f'{s.kod} şablonda yok; şablona satır eklenmez.', i)])
        return yanit({'satirlar': kd.takvim_sablonu(b)})


# ---------------------------------------------------------------- genel

GENEL = ('firma', 'varsayilan_metinler', 'varsayilan_gecerlilik_gun', 'varsayilan_para_birimi', 'cevap_uyari_gun',
         'yonetim_birimleri')


def _genel(b):
    a = ayar_deposu.hepsi(b)
    return {**{k: a.get(k) for k in GENEL}, 'para_birimleri': kd.para_birimleri(b)}


@yol.get('/ayarlar/genel')
def genel(bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit(_genel(b))


@yol.put('/ayarlar/genel')
def genel_kaydet(govde: GenelAyarlar, bg: Baglam = Depends(_ayarlayabilir)):
    an, kim = baglanti.simdi(), bg.kisi.kimlik
    with vt.islem() as b:
        eski = ayar_deposu.oku(b, 'yonetim_birimleri', [])
        if sorted(eski) != sorted(govde.yonetim_birimleri):
            if not bg.kisi.yonetim_birimlerini_degistirebilir:
                raise hatalar.yetki('Yönetim birimlerini yalnızca yetkili değiştirir.')
            bg.birim_denetle(govde.yonetim_birimleri, 'yonetim_birimleri')
        for p in govde.para_birimleri:
            if not kd.para_birimi_aktif(b, p.kod, p.aktif):
                raise hatalar.dogrulama([hatalar.hata('para_birimleri', f'{p.kod} tanımlı değil.')])
        aktif = {p['kod'] for p in kd.para_birimleri(b) if p['aktif']}
        if govde.varsayilan_para_birimi not in aktif:
            raise hatalar.dogrulama([hatalar.hata('varsayilan_para_birimi', 'Varsayılan para birimi aktif olmalı.')])
        d = govde.model_dump()
        for k in GENEL:
            ayar_deposu.yaz(b, k, d[k], kim, an)
        return yanit(_genel(b))


# ---------------------------------------------------------------- geçmiş proje formu

def _gecmis_denetle(b, bg, p, haric=None):
    bg.birim_denetle([s.birim for s in p.saatler], 'saatler.birim')
    if not kd.makine_turu(b, p.makine_turu):
        raise hatalar.dogrulama([hatalar.hata('makine_turu', f'{p.makine_turu} tanımlı değil.')])
    if gecmis_deposu.kod_var(b, p.proje_kodu, haric):
        raise hatalar.dogrulama([hatalar.hata('proje_kodu', f'{p.proje_kodu} zaten girilmiş.')])
    if len({s.birim for s in p.saatler}) != len(p.saatler):
        raise hatalar.dogrulama([hatalar.hata('saatler.birim', 'Her birim bir kez girilir.')])


@yol.get('/gecmis-projeler')
def gecmis_projeler(bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'projeler': gecmis_deposu.liste(b)})


@yol.post('/gecmis-projeler', status_code=201)
def gecmis_proje_ekle(govde: GecmisProje, bg: Baglam = Depends(_ayarlayabilir)):
    """Proje kodu serbest metindir; çekirdekte olmayabilir (eski projeler)."""
    with vt.islem() as b:
        _gecmis_denetle(b, bg, govde)
        kimlik = gecmis_deposu.ekle(b, govde.model_dump(), bg.kisi.kimlik, baglanti.simdi())
        return yanit(gecmis_deposu.bul(b, kimlik), 201)


@yol.put('/gecmis-projeler/{kimlik}')
def gecmis_proje_guncelle(kimlik: int, govde: GecmisProje, bg: Baglam = Depends(_ayarlayabilir)):
    with vt.islem() as b:
        _gecmis_denetle(b, bg, govde, kimlik)
        if not gecmis_deposu.guncelle(b, kimlik, govde.model_dump()):
            raise hatalar.bulunamadi()
        return yanit(gecmis_deposu.bul(b, kimlik))
