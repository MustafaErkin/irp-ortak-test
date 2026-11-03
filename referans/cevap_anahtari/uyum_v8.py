"""Yalniz paket oynaticisinin eski ozet surumu uyarlayicisi.

Bir V8 ozeti ancak mevcut V9 kaydinin V8 alanlariyla hesaplanan ozetine
tam esitse eslenir. Bayat/bilinmeyen ozetler ve asil olay yolu degismez.
"""
from copy import deepcopy
from irp.kabul import nesne
from irp.surum import ozet,is_alanlari

YENI={
    'ETAP': {'sorumlu'},  # V9 → V10: eski alan özeti tam eşleşmelidir.
    'PROJE': {'kimlik','ek','kod_gecmisi','ana_proje','sorumlu','baslangic_tarihi','kesin_kabul_tarihi'},
    'GOREV': {'oncelik','degisiklik_kaynagi','gecikme_nedeni','gecikme_aciklamasi'},
    'NESNE': {'kod_gecmisi'},
}


def olay_uyarla(d,e):
    sonuc=deepcopy(e); eslenen=0
    for h in sonuc.get('neyin_ustunde',[]):
        x=nesne(d,h['tur'],h['kimlik'])
        if not x or h.get('surum')==x.get('surum'): continue
        alanlar=YENI.get(h['tur'])
        if not alanlar: continue
        eski={k:v for k,v in x.items() if k not in alanlar}
        if h.get('surum')==ozet(is_alanlari(eski)):
            h['surum']=x['surum']; eslenen+=1
    return sonuc,eslenen


class Kopru:
    def __init__(self): self.eslenen=0
    def __enter__(self):
        from irp import Depo
        self.asil=Depo.olay_ekle
        def ekle(d,e,*a,**kw):
            yeni,n=olay_uyarla(d,e); self.eslenen+=n
            return self.asil(d,yeni,*a,**kw)
        Depo.olay_ekle=ekle
        return self
    def __exit__(self,*exc):
        from irp import Depo
        Depo.olay_ekle=self.asil
