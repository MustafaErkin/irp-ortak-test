"""GET /api/ben: oturumdaki kişi."""
from fastapi import APIRouter, Depends

from ..alan import notlar
from .bagimlilik import baglam

yonlendirici = APIRouter(tags=['ben'])


@yonlendirici.get('/ben')
def ben(b=Depends(baglam)):
    k = b.ben
    return b.yanit({'kimlik': k['kimlik'], 'ad': k.get('ad'), 'birim': k.get('birim'), 'roller': k.get('roller', []),
                    'yetkili': b.yetkili, 'gorulmemis_not_sayisi': len(notlar.gorulmemis_not_gorevleri(b))})
