"""I76-I90: T8 sonuclarini bagimsiz aralik ve yetki hesaplariyla denetler."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from .saat import an,gun,gun_ani
from .takvim_v7 import kesisim,pencere,birim_kapsamda

TANIMLAR={
 'I76':'Onayli izinle calisma araligi kesismez.',
 'I77':'Kapsamdaki durusla calisma araligi kesismez.',
 'I78':'Fazla mesai araligi onayli kisi penceresinde kalir.',
 'I79':'Bilinen fazla mesai primi negatif degildir.',
 'I80':'Onaylanan ozet degistiyse rapor DEGISTI olur.',
 'I81':'Plan surumlerinin sira numarasi ve onay anindaki etap kopyasi sabittir.',
 'I82':'Ret paylari toplami 100u asmaz; yalniz dogrulanmis itirazsiz paylar performanstadir.',
 'I83':'Kapanmis ayin kaynak kayitlari yeniden hesapta degismez.',
 'I84':'Acik duzeltme ile onceki donem defterinin butun farki korunur.',
 'I85':'Nesnenin her asamasi ve gecisi tur tanimindadir.',
 'I86':'Gorunurluk matris disinda izin vermez; parasal alanlar yalniz YETKILI.',
 'I87':'Maas yoklugu saat maliyetinde VERI_EKSIK olur.',
 'I88':'Araliklar kisi basina cakismayan pozitif surelerdir.',
 'I89':'Saat maliyeti maas ve gider toplaminin tarihli firma paydasina bolumudur.',
 'I90':'Kaynaklardan tam hesap ve kapsamli son hal aynidir.'}


def denetle(d,derin=False):
    from .gorunum_v7 import (fazla_mesai_kayitlari,gun_sonu_raporu,ozet_surumu,sorumluluk_performansi,
        gorebilir_mi,saat_maliyeti,duzeltme_defteri,onceki_donem_duzeltmeleri)
    from .gorunumler import tutar_bul,ay_sinirlari
    s=dict.fromkeys(TANIMLAR,True); gruplar=defaultdict(list)
    for a in d.araliklar:
        if not a['kisi']: continue
        p,q=a['baslangic'],a['bitis'] or d.saat.simdi(); gruplar[a['kisi']].append((p,q))
        if a['kova'] in ('CALISMA','YENIDEN_ISLEME'):
            s['I76'] &= not any(x['kisi']==a['kisi'] and x['durum']=='ONAYLI' and kesisim(p,q,an(x['baslangic']),an(x['bitis'])) for x in d.izinler.values())
            s['I77'] &= not any(birim_kapsamda(d,d.kisiler[a['kisi']]['birim'],x['kapsam']) and kesisim(p,q,x['baslangic'],x['bitis'] or d.saat.simdi()) for x in d.duruslar.values())
        if a.get('fazla_mesai'):
            s['I78'] &= a['kova'] in ('CALISMA','YENIDEN_ISLEME') and any(x['kisi']==a['kisi'] and not x['iptal'] and pencere(x)[0]<=p<q<=pencere(x)[1] for x in d.ek_mesai_planlari.values())
    for araliklar in gruplar.values():
        es=sorted(araliklar); s['I88'] &= all(p<q for p,q in es) and all(es[n-1][1]<=es[n][0] for n in range(1,len(es)))
    s['I79']=all(x['prim']=='VERI_EKSIK' or x['prim']>=0 for x in fazla_mesai_kayitlari(d))
    for r in d.gun_sonu_raporlari.values():
        v=gun_sonu_raporu(d,r['kisi'],r['gun'])
        if v['durum']=='ONAYLANDI': s['I80'] &= v.get('onaylanan_ozet_surumu')==ozet_surumu(v['ozet'])
        if r['durum']=='ONAYLANDI' and r.get('onaylanan_ozet_surumu')!=v['ozet_surumu']: s['I80'] &= v['durum']=='DEGISTI'
    for p,ss in d.plan_surumleri.items():
        s['I81'] &= [x['no'] for x in ss]==['B'+str(n) for n in range(len(ss))]
        if derin:
            from .motor import Motor
            from .saat import Saat
            for x in ss:
                m=Motor(Saat(x['onay_ani'])); m.yurut(list(d.olaylar.values()))
                s['I81'] &= m.plan_surumleri[p][int(x['no'][1:])]==x
    retler=defaultdict(float)
    for x in d.sorumluluklar.values(): retler[x['ret']]+=x['yuzde']; s['I82'] &= 0<=x['yuzde']<=100
    s['I82'] &= all(v<=100 for v in retler.values())
    for k in d.kisiler:
        bek=sum(x['yuzde']/100 for x in d.sorumluluklar.values() if x.get('kaynak_turu')!='GECIKME' and x['tur']=='KISI' and x['kimlik']==k and x['dogrulandi'] and not x['itirazda'])
        s['I82'] &= abs(sorumluluk_performansi(d,k,'1900-01-01','2100-01-01')['kalite_ret']-bek)<1e-9
        yetkili='YETKILI' in d.kisiler[k]['roller']
        from .yetki_v6 import istihdamda
        for tur in ('MAAS','SAAT_MALIYETI','TUTAR','MALIYET','PROJE_TUTAR'):
            s['I86'] &= gorebilir_mi(d,k,tur,'K041')==(yetkili and istihdamda(d,k,d.saat.simdi()))
        s['I86'] &= not gorebilir_mi(d,k,'TANIMSIZ_TUR','K041')
        tarih=d.saat.simdi().date(); maas=tutar_bul(d,k,'MAAS_AYLIK',tarih,None); oran=saat_maliyeti(d,k,tarih)
        if maas is None: s['I87'] &= oran=='VERI_EKSIK'
        else: s['I89'] &= abs(oran*Decimal(str(d.ayar('maas_paydasi_saat',gun_ani(tarih),180)))-Decimal(str(maas))-Decimal(str(tutar_bul(d,k,'GENEL_GIDER_PAYI',tarih,0))))<Decimal('0.000001')
    for x in d.nesneler.values():
        tur=d.nesne_turleri[x['tur']]; asamalar={a['kod'] if isinstance(a,dict) else a for a in tur['asamalar']}
        yol=[z['asama'] for z in x['asama_gecmisi']]+[x['asama']]
        s['I85'] &= set(yol)<=asamalar and all(any(g['den']==a and g['e']==b for g in tur['gecisler']) for a,b in zip(yol,yol[1:]))
    duzeltmeler=onceki_donem_duzeltmeleri(d)
    for key,eski in d.ay_kapanislari.items():
        if not key.endswith(':DEFTER_V7'): continue
        ay=key[:10]; a,b=ay_sinirlari(ay); yeni=duzeltme_defteri(d,ay)
        once=[x for ad,ss in d.ay_kapanislari.items() if ad.endswith(':DUZELTMELER') for x in ss]+duzeltmeler
        for k in set(eski)|set(yeni):
            x=yeni.get(k,dict(saat=0,tutar=Decimal(0))); y=eski.get(k,dict(saat=0,tutar=Decimal(0)))
            fark=[v for v in once if v['kaynak_ay']==ay and v['anahtar']==k]
            s['I84'] &= abs(x['saat']-y['saat']-sum(v['saat'] for v in fark))<1e-7
            if 'VERI_EKSIK' not in (x['tutar'],y['tutar']) and all(v['tutar']!='VERI_EKSIK' for v in fark): s['I84'] &= x['tutar']-y['tutar']==sum(v['tutar'] for v in fark)
    if derin:
        from .depo import Depo
        z=Depo(d.saat,'tam'); z._kayitlar=deepcopy(d._kayitlar); z.hassas_ekler=deepcopy(d.hassas_ekler); z.ay_kapanislari=deepcopy(d.ay_kapanislari)
        z.cihaz_esitlemeleri=deepcopy(d.cihaz_esitlemeleri); z.isleme_hatalari=deepcopy(d.isleme_hatalari); z.kurulum_tamamlandi=d.kurulum_tamamlandi; z.kod_listeleri=deepcopy(d.kod_listeleri)
        # T10 kalıcı kapı tablosu Motorun olay girdisine eklenmez; kurtarmada ayrı taşınır.
        z.modul_bildirimleri=deepcopy(d.modul_bildirimleri); z.yeniden_kur()
        s['I90']=d.son_hal()==z.son_hal(); s['I83']=d.ay_kapanislari==z.ay_kapanislari
    return {k:bool(v) for k,v in s.items()}
