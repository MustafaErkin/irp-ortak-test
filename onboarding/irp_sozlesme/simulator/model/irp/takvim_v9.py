"""Tarihsel birim takvimi; firmaya ozel gun tanimi her zaman ustundur."""
from copy import deepcopy
from datetime import timedelta
from .saat import an, gun, gun_ani


def hazirla(m, es):
    m._v9_birim_takvimleri={}
    m._v9_kisi_birimleri={}
    for e in es:
        kod,g=e['eylem_kodu'],e['girdiler']
        if kod=='BIRIM.TANIMLADIM' and g.get('takvim'):
            m._v9_birim_takvimleri.setdefault(g['kod'],[]).append((gun(g['takvim_gecerli']),e['olay_kimligi'],deepcopy(g['takvim'])))
        if kod=='KISI.EKLEDIM':
            m._v9_kisi_birimleri.setdefault(g['kod'],[]).append((an(g['giris_tarihi']),e['olay_kimligi'],g['birim']))
        elif kod=='KISI.DEGISTIRDIM' and 'birim' in g['degisenler']:
            m._v9_kisi_birimleri.setdefault(g['kisi'],[]).append((an(g['gecerli_baslangic']),e['olay_kimligi'],g['degisenler']['birim']))


def kisi_birimi(d,kisi,tarih):
    # Tarihle sorulan gunun takvimi gun basindaki birime sabitlenir.
    t=gun_ani(gun(tarih))
    uygun=[s for s in getattr(d,'_v9_kisi_birimleri',{}).get(kisi,[]) if s[0]<=t]
    return max(uygun)[2] if uygun else d.kisiler.get(kisi,{}).get('birim')


def birim_takvimi(d,tarih,kisi=None,birim=None):
    b=birim or (kisi_birimi(d,kisi,tarih) if kisi else None)
    uygun=[s for s in getattr(d,'_v9_birim_takvimleri',{}).get(b,[]) if s[0]<=gun(tarih)]
    if not uygun: return None
    s=deepcopy(max(uygun,key=lambda x:(x[0],x[1]))[2])
    s['calisma_gunleri']=s['gunler']
    return s


def sistem_noktalari(m,tarihler,sinir):
    sonuc=set()
    for tarih in tarihler:
        # Ayni takvimi kullanan yuzlerce kisi icin ayni siniri uretme.
        for birim in {None}|set(getattr(m,'_v9_birim_takvimleri',{})):
            if not m.is_gunu(tarih,birim=birim): continue
            t=m.takvim(tarih,birim=birim)
            noktalar=[(x['bas'],'MOLA_BASI') for x in t['sabit_molalar']]+[(x['bit'],'MOLA_SONU') for x in t['sabit_molalar']]+[(t['mesai_bitis'],'PAYDOS')]
            for saat,kod in noktalar:
                zaman=gun_ani(tarih,saat)
                if zaman<=sinir: sonuc.add((zaman,0,kod,None))
    return list(sonuc)


def nokta_kisiye_ait(m,kisi,kod,t):
    tak=m.takvim(t,kisi)
    if kod=='PAYDOS': return t==gun_ani(t.date(),tak['mesai_bitis'])
    if kod in ('MOLA_BASI','MOLA_SONU'):
        return any(t==gun_ani(t.date(),x['bas' if kod=='MOLA_BASI' else 'bit']) for x in tak['sabit_molalar'])
    return True


def gun_agirligi(d,tarih,kisi=None):
    from .takvim_v7 import normal,saatler,saat_ani
    tak=birim_takvimi(d,tarih,kisi)
    if tak:
        standart=(saat_ani(tarih,tak['mesai_bitis'])-saat_ani(tarih,tak['mesai_baslangic'])).total_seconds()/3600
        standart-=sum((saat_ani(tarih,x['bit'])-saat_ani(tarih,x['bas'])).total_seconds()/3600 for x in tak['sabit_molalar'])
    else: standart=d.ayar('standart_gunluk_saat',gun_ani(tarih),9)
    return saatler(normal(d,tarih,kisi=kisi))/standart
