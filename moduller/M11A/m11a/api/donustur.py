"""Siparişe dönüştür uçları (SPEC › 8.1, 9)."""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..alan import donusturme
from .baglam import Istek, istek

yol = APIRouter()


@yol.get('/donustur/secenekler')
def secenekler(i: Istek = Depends(istek)):
    from ..alan import yetki
    i.rol_gerek(yetki.DONUSTURME)
    return i.cekirdek.oturum(i.anahtar).oku('M10.KAZANAN_SURUMLER').deger


class DosyaGirdi(BaseModel):
    ad: str
    konum: str
    parmak_izi: str | None = None
    aciklama: str | None = None


class DonusturGirdi(BaseModel):
    surum: int
    proje_kodu: str | None = None
    proje_adi: str
    sorumlu: str
    siparis_tarihi: date
    teslim_tarihi: date
    kesin_kabul_tarihi: date | None = None
    po_no: str | None = None
    po_dosyasi: DosyaGirdi | None = None
    sozlesme_dosyasi: DosyaGirdi | None = None


@yol.get('/donustur/onizleme')
def onizleme(surum: int, i: Istek = Depends(istek)):
    return donusturme.onizleme(i, surum)


@yol.post('/donustur')
def donustur(g: DonusturGirdi, i: Istek = Depends(istek)):
    if g.proje_kodu is not None and not g.proje_kodu.strip():
        g.proje_kodu = None
    return donusturme.donustur(i, g)


@yol.post('/donustur/{proje}/yeniden-dene')
def yeniden_dene(proje: str, i: Istek = Depends(istek)):
    return donusturme.yeniden_dene(i, proje)
