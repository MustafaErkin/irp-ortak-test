"""Plan uçları (SPEC › 8.2, 9)."""
from fastapi import APIRouter, Depends

from ..alan import acilis, gonderim, plan
from .bagimlilik import baglam
from .semalar import Taslak

yonlendirici = APIRouter(prefix='/projeler/{proje}/plan', tags=['plan'])


@yonlendirici.get('')
def plan_durumu(proje: str, b=Depends(baglam)):
    return b.yanit(plan.plan_durumu(b, proje))


@yonlendirici.put('/taslak')
def taslak_kaydet(proje: str, govde: Taslak, b=Depends(baglam)):
    return b.yanit(plan.taslak_kaydet(b, proje, govde.sozluk()))


@yonlendirici.delete('/taslak')
def taslak_sil(proje: str, b=Depends(baglam)):
    return b.yanit(plan.taslak_sil(b, proje))


@yonlendirici.post('/gonder')
def gonder(proje: str, b=Depends(baglam)):
    sonuc = gonderim.gonder(b, proje)
    acilis.degerlendir(b, proje)
    return b.yanit(sonuc)


@yonlendirici.post('/satirlar/{sira}/yeniden-oku')
def yeniden_oku(proje: str, sira: int, b=Depends(baglam)):
    return b.yanit(gonderim.yeniden_oku(b, proje, sira))
