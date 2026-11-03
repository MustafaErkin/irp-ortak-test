"""I91-I105: T9 kaynak kayitlari, yetki ve hesap korunumu."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from .saat import an,gun

TANIMLAR={
    'I91':'Proje kodu ve eki gecmiste baska kimlige verilmez.',
    'I92':'Proje kimligi sabittir; kod gecmisinin son acik satiri guncel kodudur.',
    'I93':'Degisiklik baglari ayni projededir ve dongusuzdur.',
    'I94':'Degerlendirme olayinin ilk paylari tam 100dur; satirlar tekildir.',
    'I95':'Gorulme ani alicinin ilk etkin GORDUM olayidir.',
    'I96':'HERKES ayarinda istihdamdaki kisiler tum projeleri gorur.',
    'I97':'Bilinen onay bekleyen maliyet negatif degildir ve toplami asmaz.',
    'I98':'Servis bagi tek seviyedir ve var olan projeye gider.',
    'I99':'Gun onayi kimsenin kendi gununu onaylamaz.',
    'I100':'Birim takvimi normal yolda en erken ertesi gun baslar.',
    'I101':'IK kendi iznini IK asamasinda onaylamaz.',
    'I102':'Normal ve degisiklik gorevlerinin zaman katkisi 0 ile 1 arasindadir.',
    'I103':'Makinenin bildirilen bitisi BASLAT ile AL arasindadir.',
    'I104':'Nesne turu ve kodu gecmiste baska nesneye verilmez.',
    'I105':'Degisiklik dogumu kaynak kaydin alanlarini degistirmez.',
}


def denetle(d,derin=False):
    from .kurallar_v9 import olaylar,bildirim_kimligi,makine_baslangici
    from .gorunum_v9 import proje_gorebilir_mi,zaman_katkisi
    from .yetki_v6 import istihdamda
    from .gorunumler import iscilik_maliyeti,maas_dagilimi,ay_sinirlari
    from .kapilar_v3 import dongusuz
    s=dict.fromkeys(TANIMLAR,True); kodlar={}; nesneler={}
    for k,p in d.projeler.items():
        s['I92'] &= p['kimlik']==k and bool(p['kod_gecmisi'])
        for h in p['kod_gecmisi']:
            c=(h['kod'],h['ek']); s['I91'] &= c not in kodlar or kodlar[c]==k; kodlar[c]=k
        son=p['kod_gecmisi'][-1]; s['I92'] &= son['bitis'] is None and (son['kod'],son['ek'])==(p['kod'],p['ek'])
        for a,b in zip(p['kod_gecmisi'],p['kod_gecmisi'][1:]): s['I92'] &= a['bitis']==b['baslangic']
        if p.get('ana_proje'): s['I98'] &= p['ana_proje'] in d.projeler and not d.projeler[p['ana_proje']].get('ana_proje')
    tablo=dict(d.isler,**d.gorevler); graf={k:[] for k in tablo}
    for k,x in tablo.items():
        kaynak=x.get('degisiklik_kaynagi')
        if kaynak:
            s['I93'] &= kaynak in tablo and tablo[kaynak].get('proje')==x.get('proje'); graf[k]=[kaynak]
        if x.get('makine_bitis_ani'):
            bas=makine_baslangici(d,x); s['I103'] &= bool(bas) and bas<=x['makine_bitis_ani']<=x['bitis_ani']
    s['I93'] &= dongusuz(graf)
    for ev in d.gecikme_degerlendirmeleri.values():
        ss=ev['sorumlular']; s['I94'] &= sum(Decimal(str(x['yuzde'])) for x in ss)==100 and len({(x['tur'],x['kimlik']) for x in ss})==len(ss)
    for key,b in d.bildirimler.items():
        if not b['gecerli']: continue
        ts=[x['an'] for x in d.bildirim_gorulmeleri.values() if x['kim']==b['alici'] and x['an']>=b['an'] and (key in x['bildirimler'] or bildirim_kimligi(b) in x['bildirimler'])]
        s['I95'] &= b.get('gorulme_ani')==(min(ts) if ts else None)
    if d.ayar('proje_gorunurlugu',d.saat.simdi(),'HERKES')=='HERKES':
        s['I96']=all(proje_gorebilir_mi(d,k,p) for k in d.kisiler if istihdamda(d,k,d.saat.simdi()) for p in d.projeler)
    es=olaylar(d)
    for e in es:
        g=e['girdiler']; kod=e['eylem_kodu']
        if kod=='GUN_SONU.ONAYLADIM': s['I99'] &= all(x['kisi']!=e['kim'] for x in g.get('gunler',[g]))
        if kod=='BIRIM.TANIMLADIM' and g.get('takvim') and e['giris_sekli']!='AKTARIM': s['I100'] &= gun(g['takvim_gecerli'])>an(e['oldugu_an']).date()
        if kod=='IZIN.IK_ONAYLADIM': s['I101'] &= d.izinler[g['hedef']]['kisi']!=e['kim']
    for x in d.gorevler.values():
        if x['tur'] in ('NORMAL','DEGISIKLIK') and x.get('ilk_teslim_ani'): s['I102'] &= 0<=zaman_katkisi(d,x)<=1
    for k,x in d.nesneler.items():
        for h in x.get('kod_gecmisi',[]):
            key=(x['tur'],h['kod']); s['I104'] &= key not in nesneler or nesneler[key]==k; nesneler[key]=k
    if d.gun_onay_ayarlari:
        a,b=ay_sinirlari(d.saat.simdi().date())
        for p in d.projeler:
            x=iscilik_maliyeti(d,p,a,b)
            if x['iscilik']!='VERI_EKSIK' and x['onay_bekleyen']!='VERI_EKSIK': s['I97'] &= 0<=x['onay_bekleyen']<=x['iscilik']
        for k in d.kisiler:
            x=maas_dagilimi(d,k,a)
            if x['onay_bekleyen']!='VERI_EKSIK' and all(t!='VERI_EKSIK' for t in x['tutarlar'].values()): s['I97'] &= 0<=x['onay_bekleyen']<=sum(x['tutarlar'].values())+Decimal('0.01')
    if derin:
        from .motor import Motor
        from .saat import Saat
        for e in es:
            ss=e['girdiler'].get('gorevler',e['girdiler'].get('isler',[e['girdiler']]))
            kaynaklar=[x['degisiklik']['kaynak'] for x in ss if x.get('degisiklik')]
            if not kaynaklar: continue
            once=Motor(Saat(e['oldugu_an'])); sonra=Motor(Saat(e['oldugu_an']))
            kaynak=[x for x in es if (an(x['oldugu_an']),x['olay_kimligi'])<(an(e['oldugu_an']),e['olay_kimligi'])]
            once.yurut(kaynak); sonra.yurut(kaynak+[e])
            for k in kaynaklar: s['I105'] &= dict(once.isler,**once.gorevler).get(k)==dict(sonra.isler,**sonra.gorevler).get(k)
    return {k:bool(v) for k,v in s.items()}
