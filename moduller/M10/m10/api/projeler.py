"""Bağlı proje (ek iş ve servis): kullanıcının gözüyle PROJE okunur, yalnızca kimliği tutulur (SPEC › 8.2).

PROJELER simülatörde yok; liste gösterilemez, kod elle yazılır (istek M10-06).
"""
from fastapi import APIRouter, Depends

from irp_sozlesme.baglanti import CekirdekHatasi

from .. import hatalar
from .baglam import Baglam, erisimli
from .yanit import yanit

yol = APIRouter()

GOREMIYOR = 'Bu projeyi göremiyorsunuz; bağlamak için projede erişiminiz olmalı.'


def proje_oku(bg: Baglam, kod):
    """→ {kod, ad}. Göremiyorsa 403 (etrafından dolaşılmaz), yoksa 404."""
    try:
        p = bg.oku('PROJE', kod)
    except CekirdekHatasi as e:
        if e.tur == 'YETKI':
            raise hatalar.yetki(GOREMIYOR) from None
        raise
    if not p:
        raise hatalar.bulunamadi(f'{kod} kodlu proje bulunamadı.')
    return {'kod': p['kimlik'], 'ad': p.get('ad')}


def proje_ozeti(bg: Baglam, kod):
    """Talep kartı için: göremese de kodu gösterilir, adı gösterilmez."""
    if not kod:
        return None
    try:
        return dict(proje_oku(bg, kod), gorunur=True)
    except hatalar.ModulHatasi:
        return {'kod': kod, 'ad': None, 'gorunur': False}


@yol.get('/projeler/{kod}')
def proje(kod: str, bg: Baglam = Depends(erisimli)):
    return yanit(proje_oku(bg, kod.strip()), baglam=bg)
