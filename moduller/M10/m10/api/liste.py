"""Talepler listesi, arama, sayaç şeridi ve onay bekleyenler (SPEC › 8.13, 8.10)."""
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Query

from .. import baglanti, vt
from ..alan import durum
from ..alan.arama import kelimeler
from ..depo import ayarlar as ayar_deposu
from ..depo import talepler as td
from .baglam import Baglam, erisimli, onayci
from .yanit import yanit

yol = APIRouter()


@yol.get('/talepler')
def talepler(q: str = '', musteri: int | None = None, makine_turu: str | None = None,
             talep_durumu: str | None = Query(default=None, alias='durum'), yil: int | None = None,
             bg: Baglam = Depends(erisimli)):
    """Arama: sorgunun her kelimesi arama metninde geçer (VE). Süzgeçler: müşteri, makine türü, durum, yıl."""
    bugun = baglanti.simdi().date()
    with vt.islem() as b:
        uyari_gun = ayar_deposu.oku(b, 'cevap_uyari_gun', 3)
        satirlar = td.liste(b, kelimeler(q), musteri, makine_turu, talep_durumu, yil)
    for t in satirlar:
        t['isaret'] = durum.cevap_isareti(t['durum'], t['gonderilmis'], t['cevap_tarihi'], bugun, uyari_gun)
    return yanit({'talepler': satirlar}, baglam=bg)


@yol.get('/talepler/sayac')
def sayac(yil: int | None = None, bg: Baglam = Depends(erisimli)):
    """Sayaç şeridi; varsayılan yıl çekirdeğin saatine göre bu yıl."""
    yil = yil or baglanti.simdi().year
    with vt.islem() as b:
        r = td.sayac(b, yil)
    toplam = r['kazanilan'] + r['kaybedilen']
    oran = None if not toplam else (Decimal(100) * r['kazanilan'] / toplam).quantize(Decimal('0.1'), ROUND_HALF_UP)
    return yanit({'yil': yil, 'kazanilan': r['kazanilan'], 'kaybedilen': r['kaybedilen'],
                  'kazanma_orani': None if oran is None else float(oran),
                  'kayip_nedenleri': {'FIYAT': r['fiyat'], 'TEKNIK_COZUM': r['teknik_cozum'],
                                      'TESLIM_SURESI': r['teslim_suresi']},
                  'acik': r['acik']})


@yol.get('/onay-bekleyenler')
def onay_bekleyenler(bg: Baglam = Depends(onayci)):
    """"Onayınızı bekleyen teklifler": iş listesidir, bildirim kutusu değildir (istek M10-01)."""
    with vt.islem() as b:
        satirlar = td.onay_bekleyenler(b)
    for s in satirlar:
        s['etiket'] = f'{s["talep_no"]}/V{s["no"]}'
        s['hazirlayan_adi'] = bg.kisi_adi(s['hazirlayan'])
    return yanit({'surumler': satirlar}, baglam=bg)
