"""Kişi, seçim listeleri, geliştirme girişi (SPEC › 9)."""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..alan import yetki
from .baglam import Istek, Uygulama, istek
from .hatalar import ModulHatasi

yol = APIRouter()


@yol.get('/ben')
def ben(i: Istek = Depends(istek)):
    k = i.kisi_kaydi
    return i.cevap({'kisi': k['kimlik'], 'ad': k['ad'], 'birim': k.get('birim'), 'roller': sorted(i.roller),
                    'izinler': yetki.izinler(i.roller)})


@yol.get('/kisiler')
def kisiler(i: Istek = Depends(istek)):
    return i.cevap({'kisiler': [{'kimlik': k['kimlik'], 'ad': k['ad'], 'birim': k.get('birim'),
                                 'roller': k.get('roller', [])} for k in i.kisiler() if k.get('aktif')]})


@yol.get('/birimler')
def birimler(i: Istek = Depends(istek)):
    return i.cevap({'birimler': [{'kimlik': b['kimlik'], 'ad': b['ad']} for b in i.oku('BIRIMLER') or []]})


class Giris(BaseModel):
    kisi: str


@yol.post('/gelistirme/giris')
def gelistirme_giris(g: Giris, request: Request):
    """Yalnızca M11A_GELISTIRME=1. Üründe kullanıcı çekirdeğin girişiyle girer; modül şifre görmez."""
    u: Uygulama = request.app.state.m11a
    if not u.gelistirme:
        raise ModulHatasi(404, 'BULUNAMADI', 'Geliştirme girişi kapalı.')
    oturum = u.cekirdek.giris(g.kisi.strip().upper(), 'gelistirme')
    return {'kisi': oturum.kisi, 'anahtar': oturum.anahtar}
