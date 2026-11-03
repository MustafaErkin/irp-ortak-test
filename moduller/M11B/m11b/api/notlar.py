"""Bilgi notları ve "görülmemiş notlarım" (SPEC › 8.6)."""
from fastapi import APIRouter, Depends

from ..alan import acilis, notlar
from .bagimlilik import baglam
from .semalar import BilgiNotu

yonlendirici = APIRouter(tags=['notlar'])


@yonlendirici.get('/projeler/{proje}/notlar')
def not_listesi(proje: str, b=Depends(baglam)):
    return b.yanit(notlar.not_listesi(b, proje))


@yonlendirici.get('/projeler/{proje}/notlar/{not_kimligi}')
def not_ayrintisi(proje: str, not_kimligi: str, b=Depends(baglam)):
    return b.yanit(notlar.not_ayrintisi(b, proje, not_kimligi))


@yonlendirici.post('/projeler/{proje}/notlar')
def not_yaz(proje: str, govde: BilgiNotu, b=Depends(baglam)):
    sonuc = notlar.not_yaz(b, proje, govde.model_dump())
    acilis.degerlendir(b, proje)
    return b.yanit(sonuc)


@yonlendirici.get('/notlarim')
def notlarim(b=Depends(baglam)):
    return b.yanit(notlar.notlarim(b))


@yonlendirici.post('/notlarim/{gorev:path}/gordum')
def gordum(gorev: str, b=Depends(baglam)):
    return b.yanit(notlar.gordum(b, gorev))
