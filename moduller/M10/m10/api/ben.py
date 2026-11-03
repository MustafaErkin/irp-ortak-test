"""Kişi, seçim listeleri ve geliştirme girişi."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import ayarlar, baglanti, hatalar, vt
from .baglam import Baglam, baglam, erisimli
from .yanit import yanit

yol = APIRouter()


@yol.get('/ben')
def ben(bg: Baglam = Depends(baglam)):
    """Erişimi olmayan da kendini görür; ekran ona "erişiminiz yok" der."""
    k = bg.kisi
    bekleyen = 0
    if k.onayci:
        with vt.islem() as b:
            bekleyen = b.execute("SELECT count(*) AS n FROM teklif_surumleri WHERE durum = 'ONAY_BEKLIYOR'").fetchone()['n']
    return yanit({'kimlik': k.kimlik, 'ad': k.ad, 'birim': k.birim, 'roller': list(k.roller), 'erisim': k.erisim,
                  'duzenleyici': k.duzenleyici, 'onayci': k.onayci, 'onay_bekleyen': bekleyen}, baglam=bg)


@yol.get('/kisiler')
def kisiler(bg: Baglam = Depends(erisimli)):
    return yanit({'kisiler': [{'kimlik': x['kimlik'], 'ad': x.get('ad'), 'birim': x.get('birim'),
                               'aktif': x.get('aktif', True)} for x in bg.kisiler]}, baglam=bg)


@yol.get('/birimler')
def birimler(bg: Baglam = Depends(erisimli)):
    return yanit({'birimler': [{'kimlik': x['kimlik'], 'ad': x.get('ad'), 'ust': x.get('ust')}
                               for x in bg.birimler()]}, baglam=bg)


class GirisIstegi(BaseModel):
    kisi: str


@yol.post('/gelistirme/giris')
def gelistirme_girisi(g: GirisIstegi):
    """Yalnızca M10_GELISTIRME=1: örnek firmanın bir kişisi olarak girilir. Üründe giriş çekirdeğindir."""
    if not ayarlar.gelistirme():
        raise hatalar.bulunamadi()
    oturum = baglanti.cekirdek().giris(g.kisi.strip().upper(), 'gelistirme')
    return yanit({'anahtar': oturum.anahtar, 'kisi': oturum.kisi})
