"""Geliştirme girişi: yalnızca M11B_GELISTIRME=1. Üründe anahtarı çekirdeğin girişi verir (S1)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from irp_sozlesme.baglanti import CekirdekHatasi

from ..alan.hatalar import ModulHatasi
from .bagimlilik import kaynaklar

yonlendirici = APIRouter(prefix='/gelistirme', tags=['gelistirme'])


class Giris(BaseModel):
    kisi: str = Field(pattern=r'^K[0-9]{3}$')


@yonlendirici.post('/giris')
def giris(g: Giris, k=Depends(kaynaklar)):
    try:
        oturum = k.cekirdek.giris(g.kisi, 'gelistirme')
    except CekirdekHatasi:
        raise ModulHatasi(403, 'GIRIS', 'Bu kişiyle girilemiyor.') from None
    return {'anahtar': oturum.anahtar, 'kisi': oturum.kisi}
