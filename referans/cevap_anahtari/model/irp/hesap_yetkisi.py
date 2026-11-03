"""T3 §4 / T5 §5 sunucu hesabı yetki modeli; gerçek Auth servisi değildir."""
def kullanici_ac(depo, cagiran, kisi):
    from .yetki_v6 import istihdamda
    if 'YETKILI' not in depo.kisiler.get(cagiran,{}).get('roller',[]) or not istihdamda(depo, cagiran, depo.saat.simdi()):
        raise PermissionError('Yalniz YETKILI')
    if kisi not in depo.kisiler: raise ValueError('Kisi yok')
    return {'kisi':kisi,'yetki':'YETKILI','islem':'kullanici_ac'}

def sifre_sifirla(depo,cagiran,kisi):
    return dict(kullanici_ac(depo,cagiran,kisi),islem='sifre_sifirla')
