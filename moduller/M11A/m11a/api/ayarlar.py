"""Ayarlar ucu (SPEC › 8.9)."""
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..alan import ayar
from .baglam import Istek, istek

yol = APIRouter()


class SaatUcreti(BaseModel):
    birim: str
    ucret: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    para_birimi: str = Field(pattern=r'^[A-Z]{3}$')


class AyarGirdi(BaseModel):
    proje_kodu_deseni: str = Field(min_length=1)
    proje_kodu_sira_kapsami: Literal['YIL', 'AY']
    siparis_adi_deseni: str = Field(min_length=1)
    sapma_esigi_puan: Decimal = Field(ge=0, le=100, decimal_places=1)
    yaklasan_tarih_gun: int = Field(ge=1, le=365)
    saat_ucretleri: list[SaatUcreti] = []


@yol.get('/ayarlar')
def oku(i: Istek = Depends(istek)):
    return ayar.oku(i)


@yol.put('/ayarlar')
def yaz(g: AyarGirdi, i: Istek = Depends(istek)):
    return ayar.yaz(i, g)
