"""Sağlanan okumaların ucu: GET /api/saglanan/{ad}?proje= (SPEC › 8.10, Ek D.4)."""
from fastapi import APIRouter, Depends

from ..alan import saglanan
from .baglam import Istek, istek

yol = APIRouter()


@yol.get('/saglanan/{ad}')
def oku(ad: str, proje: str = '', i: Istek = Depends(istek)):
    return saglanan.oku(i, ad, proje)
