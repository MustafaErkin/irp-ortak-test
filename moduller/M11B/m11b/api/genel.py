"""Ayarlar, seçim listeleri ve sağlanan okumalar."""
from fastapi import APIRouter, Depends

from ..alan import ayarlar, saglanan
from .bagimlilik import baglam
from .semalar import SablonAyarlari

yonlendirici = APIRouter(tags=['genel'])


@yonlendirici.get('/ayarlar/sablonlar')
def sablonlar(b=Depends(baglam)):
    return b.yanit(ayarlar.sablonlar(b))


@yonlendirici.put('/ayarlar/sablonlar')
def sablonlari_kaydet(govde: SablonAyarlari, b=Depends(baglam)):
    return b.yanit(ayarlar.sablonlari_kaydet(b, govde.model_dump()))


@yonlendirici.get('/birimler')
def birimler(b=Depends(baglam)):
    return b.yanit({'birimler': [{k: x.get(k) for k in ('kimlik', 'ad', 'ust', 'basi', 'yoneticileri')}
                                 for x in b.birimler]})


@yonlendirici.get('/kisiler')
def kisiler(birim: str | None = None, b=Depends(baglam)):
    satirlar = b.oku('KISILER', birim=birim) if birim else b.kisiler
    return b.yanit({'kisiler': [{k: x.get(k) for k in ('kimlik', 'ad', 'birim', 'yaka', 'roller', 'aktif')}
                                for x in satirlar]})


@yonlendirici.get('/saglanan/{ad}')
def saglanan_okuma(ad: str, proje: str | None = None, b=Depends(baglam)):
    return b.yanit(saglanan.oku(b, ad, proje))
