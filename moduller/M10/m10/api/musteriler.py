"""Müşteriler (SPEC › 8.1). Silinmez, pasifleştirilir. İletişim kişileri kişisel veridir (künyede beyanlı)."""
from fastapi import APIRouter, Depends

from .. import baglanti, hatalar, vt
from ..depo import musteriler as md
from .baglam import Baglam, duzenleyici, erisimli
from .semalar import Musteri
from .yanit import yanit

yol = APIRouter()

AYNI_AD = 'Bu adla bir müşteri var.'


def _ayrinti(b, kimlik):
    m = md.bul(b, kimlik)
    if m is None:
        raise hatalar.bulunamadi('Müşteri bulunamadı.')
    talepler = b.execute('SELECT kimlik, talep_no, konu, durum, gelis_tarihi FROM talepler WHERE musteri = %s '
                         'ORDER BY talep_no DESC', (kimlik,)).fetchall()
    return dict(m, kisiler=md.kisiler(b, kimlik), talepler=talepler)


def _ayni_ad(b, govde, haric=None):
    benzerler = md.ayni_adli(b, govde.ad, haric)
    if benzerler and not govde.yine_de:
        raise hatalar.ModulHatasi(409, 'AYNI_AD', AYNI_AD, benzerler=benzerler)


@yol.get('/musteriler')
def liste(q: str = '', aktif: bool = False, bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit({'musteriler': md.liste(b, q, yalniz_aktif=aktif)})


@yol.post('/musteriler', status_code=201)
def ekle(govde: Musteri, bg: Baglam = Depends(duzenleyici)):
    """Normal adı aynı olan müşteri varsa 409 AYNI_AD; kullanıcı onaylarsa `yine_de: true` ile kaydedilir."""
    with vt.islem() as b:
        _ayni_ad(b, govde)
        kimlik = md.ekle(b, govde.model_dump(), bg.kisi.kimlik, baglanti.simdi())
        return yanit(_ayrinti(b, kimlik), 201)


@yol.get('/musteriler/{kimlik}')
def ayrinti(kimlik: int, bg: Baglam = Depends(erisimli)):
    with vt.islem() as b:
        return yanit(_ayrinti(b, kimlik))


@yol.put('/musteriler/{kimlik}')
def guncelle(kimlik: int, govde: Musteri, bg: Baglam = Depends(duzenleyici)):
    with vt.islem() as b:
        eski = md.bul(b, kimlik, kilitle=True)
        if eski is None:
            raise hatalar.bulunamadi('Müşteri bulunamadı.')
        if eski['ad'] != govde.ad:
            _ayni_ad(b, govde, kimlik)
        md.guncelle(b, kimlik, govde.model_dump())
        return yanit(_ayrinti(b, kimlik))
