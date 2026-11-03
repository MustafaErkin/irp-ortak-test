"""Paket 1.1 okumaları. Donmuş cevap anahtarı değiştirilmez.

Sonuç/maliyet tablolarında eski modele uydurma yanıt eklenmez; katalog bunlar
için gerçek ürün SQL'i gerektiğini belirtir. Bu dosya planlama pilotunun
PROJELER, PLAN.surumler ve GANTT.adlar/etap özeti farkını taşır.
"""
from copy import deepcopy


def oku(d,kim,veri,hedef=None,**g):
    from irp.gorunum_v7 import oku as model
    from irp.gorunum_v9 import proje_gorebilir_mi
    from irp.yetki_v6 import istihdamda
    if not istihdamda(d,kim,d.saat.simdi()):
        raise PermissionError('Oturum')
    if set(g)&{'kim','cagiran','oturum'}:
        raise PermissionError('Kullanıcı değiştirilemez')
    if veri=='PROJELER':
        return [dict(deepcopy(p),kimlik=k) for k,p in sorted(d.projeler.items())
                if proje_gorebilir_mi(d,kim,k)]
    sonuc=model(d,kim,veri,hedef,**g)
    if veri=='PLAN' and g.get('surumler'):
        sonuc['surumler']=deepcopy(d.plan_surumleri.get(hedef,[]))
    if veri=='GANTT':
        # Önce kullanıcının gerçek okuması yetkiyi doğrular. Yetkilinin tam
        # okumasından yalnız etap özeti alınır; özel görevler aktarılmaz.
        yetkili=next(k for k,p in d.kisiler.items() if 'YETKILI' in p.get('roller',[]))
        tam=model(d,yetkili,veri,hedef,**g)
        izinli={(s['tur'],s['kimlik']) for s in sonuc}
        sonuc=[s for s in tam if s['tur']=='ETAP' or (s['tur'],s['kimlik']) in izinli]
        if g.get('adlar'):
            for s in sonuc:
                tablo={'ETAP':d.etaplar,'IS':d.isler,'GOREV':d.gorevler}[s['tur']]
                x=tablo.get(s['kimlik'],{})
                s['ad']=x.get('ad') or x.get('islem')
    return sonuc
