"""T8 salt okunur sorgular; parasal eksiklik sifira donusturulmez."""
from collections import defaultdict
from copy import copy, deepcopy
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from .saat import an, gun, gun_ani, Saat
from .olay import kodla
from .takvim_v7 import (gunler, saat_ani, normal, kisi_normal, izinler, ekler, pencere,
                        cikar, saatler, kesisim, katsayi, birim_kapsamda)
from .yetki_v6 import istihdamda, ustler, yoneticiler, birim_ustleri

EKSIK='VERI_EKSIK'


def temel_gorebilir_mi(d, kim, veri, hedef=None):
    if not istihdamda(d,kim,d.saat.simdi()): return False
    yetkili='YETKILI' in d.kisiler[kim]['roller']
    if veri in ('MAAS','UCRET','SAAT_MALIYETI','TUTAR','MALIYET','PROJE_TUTAR'): return yetkili
    if veri in ('GUN','GOREV','IS','PERFORMANS','FAZLA_MESAI','IZIN','IZIN_DETAY'):
        return hedef in d.kisiler and (yetkili or kim==hedef or kim in ustler(d,hedef))
    if veri=='BIRIM_PERFORMANS': return hedef in d.birimler and (yetkili or d.kisiler[kim]['birim']==hedef or kim in yoneticiler(d,hedef)|birim_ustleri(d,hedef))
    if veri in ('PROJE_DURUM','ETAP_DURUM','UYGUNLUK','NESNE'): return True
    if veri=='HAM_OLAY': return yetkili or kim==hedef
    return False


def gorebilir_mi(d,kim,veri,hedef=None):
    from .gorunum_v9 import gorebilir_mi as v9
    return v9(d,kim,veri,hedef)


def saat_maliyeti(d,kisi,tarih):
    if kisi in d.tezgahlar:
        from .gorunum_v10_2 import tezgah_ucreti
        return tezgah_ucreti(d,kisi,tarih)
    from .gorunumler import tutar_bul
    maas=tutar_bul(d,kisi,'MAAS_AYLIK',tarih,None)
    if maas is None: return EKSIK
    gider=tutar_bul(d,kisi,'GENEL_GIDER_PAYI',tarih,0)
    payda=Decimal(str(d.ayar('maas_paydasi_saat',gun_ani(tarih),180)))
    return (Decimal(str(maas))+Decimal(str(gider)))/payda


def gun_agirligi(d,tarih,kisi=None):
    # Eski (d,tarih) ve yeni (d,kisi,tarih) cagrilari birlikte desteklenir.
    if tarih in d.kisiler and kisi is not None: tarih,kisi=kisi,tarih
    from .takvim_v9 import gun_agirligi as v9
    return v9(d,tarih,kisi)


def kapasite(d,kisi,bas,bit):
    return sum(saatler(cikar(kisi_normal(d,kisi,g)+ekler(d,kisi,g),izinler(d,kisi))) for g in gunler(bas,bit) if istihdamda(d,kisi,g))


def maas_dagilimi(d,kisi,ay,canli=False):
    from .gorunumler import ay_sinirlari,para,gorev_payi,tutar_bul
    from .gorunum_v9 import bekleyen_maliyet
    bas,bit=ay_sinirlari(ay); key=str(bas)+':'+kisi
    if not canli and key in d.ay_kapanislari: return deepcopy(d.ay_kapanislari[key]['maas'])
    paylar=defaultdict(float); tutarlar=defaultdict(Decimal); eksik=False
    for g in d.gorevler.values():
        if kisi not in {g['kisi']}|{x['kisi'] for x in g.get('kisi_gecmisi',[])}: continue
        kalem=g.get('proje') or g.get('kategori') or 'BELIRSIZ'
        if g['durum']=='IPTAL': kalem='iptal:'+kalem
        elif g['tur']=='REVIZYON': kalem='revizyon:'+kalem
        for tarih in gunler(bas,bit):
            pay=gorev_payi(d,g,tarih,tarih,kisi=kisi)
            if not pay: continue
            paylar[kalem]+=pay; oran=saat_maliyeti(d,kisi,tarih)
            if oran==EKSIK or tutarlar[kalem]==EKSIK: tutarlar[kalem]=EKSIK; eksik=True
            else: tutarlar[kalem]+=Decimal(str(pay))*oran
    toplam_agirlik=sum(gun_agirligi(d,g,kisi) for g in gunler(bas,bit))
    agirlik=sum(gun_agirligi(d,g,kisi) for g in gunler(bas,bit) if istihdamda(d,kisi,g))
    oran=agirlik/toplam_agirlik if toplam_agirlik else 0
    maas=Decimal(0)
    for tarih in gunler(bas,bit):
        if not istihdamda(d,kisi,tarih) or not gun_agirligi(d,tarih,kisi): continue
        deger=tutar_bul(d,kisi,'MAAS_AYLIK',tarih,None)
        if deger is None: maas=EKSIK; eksik=True; break
        maas+=Decimal(str(deger))*Decimal(str(gun_agirligi(d,tarih,kisi)/toplam_agirlik))
    tutarlar={k:para(v) if v!=EKSIK else v for k,v in tutarlar.items()}
    toplam=sum(v for v in tutarlar.values() if v!=EKSIK)
    return dict(paylar=dict(paylar),toplam_saat=sum(paylar.values()),payda=d.ayar('maas_paydasi_saat',gun_ani(bas),180)*oran,tutarlar=tutarlar,
                onay_bekleyen=bekleyen_maliyet(d,bas,bit,kisi=kisi,maas=True),
                dagitilamayan=EKSIK if eksik else para(max(Decimal(0),maas-toplam)),
                maasin_ustu=EKSIK if eksik else para(max(Decimal(0),toplam-maas)),maas=EKSIK if maas==EKSIK else para(maas),eksik_veri=eksik)


def iscilik_maliyeti(d,proje,bas,bit,canli=False,iptal=False):
    from .gorunumler import ay_sinirlari,para,tutar_bul
    from .gorunum_v10_1 import pencere as okuma_penceresi
    pencere_bas,pencere_bit=okuma_penceresi(bas,bit)
    a,b=ay_sinirlari(pencere_bas.date()); key=str(a)+(':IPTAL_MALIYET' if iptal else ':MALIYET')
    donmus=d.ay_kapanislari.get(key)
    if not canli and donmus is not None:
        if pencere_bas!=gun_ani(a) or pencere_bit!=gun_ani(b+timedelta(days=1)): raise ValueError('Karar 49: kapanmis ay yalniz tam ay sorgulanir')
        return deepcopy(donmus.get(proje,dict(iscilik=para(0),tezgah=para(0),eksik_veri=False)))
    toplam=dict(iscilik=Decimal(0),tezgah=Decimal(0)); eksik=False
    for x in d.araliklar:
        if x['proje']!=proje or (d.isler.get(x['is'],{}).get('durum')=='IPTAL') != iptal: continue
        if x['kova'] not in ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY','TEZGAH'): continue
        p,q=max(x['baslangic'],pencere_bas),min(x['bitis'] or d.saat.simdi(),pencere_bit)
        if p>=q: continue
        for tarih in gunler(p,q-timedelta(microseconds=1)):
            u,v=max(p,gun_ani(tarih)),min(q,gun_ani(tarih+timedelta(days=1)))
            makine=x['kova']=='TEZGAH'; alan='tezgah' if makine else 'iscilik'
            oran=tutar_bul(d,x['tezgah'],'SAAT_UCRETI',tarih,None) if makine else saat_maliyeti(d,x['kisi'],tarih)
            if oran is None or oran==EKSIK or toplam[alan]==EKSIK: toplam[alan]=EKSIK; eksik=True
            else: toplam[alan]+=Decimal(str((v-u).total_seconds()/3600))*Decimal(str(oran))
    from .gorunum_v9 import bekleyen_maliyet
    return dict({k:para(v) if v!=EKSIK else v for k,v in toplam.items()},eksik_veri=eksik,onay_bekleyen=bekleyen_maliyet(d,bas,bit,proje=proje,iptal=iptal))


def fazla_mesai_kayitlari(d):
    from .gorunumler import para
    sonuc=[]
    for a in d.araliklar:
        if not a.get('fazla_mesai'): continue
        sonuc.append(dict(kisi=a['kisi'],hedef=a['is'],proje=a['proje'],kategori=a['kategori'],tarih=str(a['gun']),baslangic=a['baslangic'],bitis=a['bitis'] or d.saat.simdi(),katsayi=a['katsayi']))
    for x in d.ek_mesai_planlari.values():
        if not x['damga'] or x['iptal'] or d.kisiler.get(x['kisi'],{}).get('yaka')!='BEYAZ': continue
        hedef=next((h['kimlik'] for h in x['hedef'] if h['tur']=='GOREV'),None)
        g=d.gorevler.get(hedef,{})
        a,b=pencere(x)
        engeller=izinler(d,x['kisi'])+[(s['baslangic'],s['bitis'] or d.saat.simdi()) for s in d.duruslar.values() if birim_kapsamda(d,d.kisiler[x['kisi']]['birim'],s['kapsam'])]
        for u,v in cikar([(a,b)],engeller):
            for tarih in gunler(u,v-timedelta(microseconds=1)):
                p,q=max(u,gun_ani(tarih)),min(v,gun_ani(tarih+timedelta(days=1)))
                sonuc.append(dict(kisi=x['kisi'],hedef=hedef,proje=g.get('proje'),kategori=g.get('kategori'),tarih=str(tarih),baslangic=p,bitis=q,katsayi=katsayi(d,tarih)))
    for x in sonuc:
        x['saat']=(x['bitis']-x['baslangic']).total_seconds()/3600
        oran=saat_maliyeti(d,x['kisi'],x['tarih'])
        x['prim']=EKSIK if oran==EKSIK else para(Decimal(str(x['saat']))*oran*Decimal(str(x['katsayi']-1)))
        x['kalem']='FAZLA_MESAI_PRIMI'
    return sonuc


def fazla_mesai_ozeti(d,kisi,ay):
    from .gorunumler import ay_sinirlari
    a,b=ay_sinirlari(ay); sonuc=defaultdict(float)
    for x in fazla_mesai_kayitlari(d):
        if x['kisi']==kisi and a<=gun(x['tarih'])<=b: sonuc[str(x['katsayi'])]+=x['saat']
    return dict(sonuc)


def aylik_maliyet_ozeti(d,kisi,ay):
    """Mavi yakanin taban isciligi ve beyaz yakanin gorev maliyeti."""
    if d.kisiler[kisi]['yaka']!='MAVI': return maas_dagilimi(d,kisi,ay)
    from .gorunumler import ay_sinirlari,para
    a,b=ay_sinirlari(ay); maas=maas_dagilimi(d,kisi,ay)['maas']; tutarlar=defaultdict(Decimal); paylar=defaultdict(float)
    defter=d.ay_kapanislari.get(str(a)+':DEFTER_V7')
    if defter is None: defter=donem_defteri(d,a,b)
    for x in defter.values():
        if x['kisi']!=kisi or x['kaynak_kalem']!='ISCILIK': continue
        kalem=x['proje']; paylar[kalem]+=x['saat']
        tutarlar[kalem]='VERI_EKSIK' if x['tutar']=='VERI_EKSIK' or tutarlar[kalem]=='VERI_EKSIK' else tutarlar[kalem]+x['tutar']
    eksik=maas=='VERI_EKSIK' or 'VERI_EKSIK' in tutarlar.values(); toplam=sum(v for v in tutarlar.values() if v!='VERI_EKSIK')
    return dict(paylar=dict(paylar),tutarlar=dict(tutarlar),maas=maas,eksik_veri=eksik,toplam_saat=sum(paylar.values()),
                dagitilamayan='VERI_EKSIK' if eksik else para(max(Decimal(0),maas-toplam)),
                maasin_ustu='VERI_EKSIK' if eksik else para(max(Decimal(0),toplam-maas)))


def kisi_uygun_mu(d,kisi,bas,bit,cagiran):
    a,b=an(bas),an(bit)
    if a>=b: raise ValueError('Aralik')
    if not gorebilir_mi(d,cagiran,'UYGUNLUK'): raise PermissionError('Gorunurluk')
    if not all(istihdamda(d,kisi,t) for t in gunler(a,b-timedelta(microseconds=1))): return dict(uygun=False,neden='istihdam disi')
    for x in d.izinler.values():
        if x['kisi']==kisi and x['durum']=='ONAYLI' and kesisim(a,b,an(x['baslangic']),an(x['bitis'])):
            return dict(uygun=False,neden='izin ('+x['tur']+')' if gorebilir_mi(d,cagiran,'IZIN_DETAY',kisi) else 'musait degil')
    izinli=[p for t in gunler(a,b) for p in normal(d,t,False,kisi)+ekler(d,kisi,t)]
    return dict(uygun=not cikar([(a,b)],izinli),neden=None if not cikar([(a,b)],izinli) else 'takvim')


def vardiyalar(d,tezgah,tarih):
    uygun=[x for x in d.tezgah_takvimleri.values() if x['tezgah']==tezgah and gun(x['gecerli_baslangic'])<=gun(tarih)]
    if not uygun: return normal(d,tarih,birim=d.tezgahlar.get(tezgah,{}).get('birim'))
    x=max(uygun,key=lambda x:(x['gecerli_baslangic'],x['kimlik']))
    return [(saat_ani(tarih,v['bas']),saat_ani(tarih,v['bit'])) for v in x['vardiyalar'] if gun(tarih).isoweekday() in v['gunler']]


def tezgah_calisma_pencereleri(d,tezgah,tarih):
    """Karar 113: vardiya ile hedef işi bu tezgâhta olan onaylı ek mesainin birleşimi."""
    from .takvim_v7 import birlesim
    a,b=gun_ani(tarih),gun_ani(gun(tarih)+timedelta(days=1))
    ek=[]
    for x in d.ek_mesai_planlari.values():
        if x.get('iptal') or not any(h['tur']=='IS' and d.isler.get(h['kimlik'],{}).get('tezgah')==tezgah for h in x['hedef']): continue
        p,q=pencere(x)
        if max(a,p)<min(b,q): ek.append((max(a,p),min(b,q)))
    return birlesim(vardiyalar(d,tezgah,tarih)+ek)


def tezgah_planli_araliklar(d,tezgah,bas,bit):
    """An penceresinde planlı kapasite; bakım ek mesaiyi de kapatır, arıza paydayı azaltmaz."""
    a,b=an(bas),an(bit)
    if tezgah not in d.tezgahlar or a>=b: raise ValueError('Tezgah/aralik')
    plan=[(max(a,p),min(b,q)) for t in gunler(a,b-timedelta(microseconds=1))
          for p,q in tezgah_calisma_pencereleri(d,tezgah,t) if max(a,p)<min(b,q)]
    bakim=[(an(x['baslangic']),an(x['bitis'])) for x in d.bakimlar.values() if x['tezgah']==tezgah and not x['iptal']]
    return cikar(plan,bakim)


def tezgah_engelleri(d,tezgah):
    b=d.tezgahlar.get(tezgah,{}).get('birim')
    return [(x['baslangic'],x['bitis'] or d.saat.simdi(),x['neden']) for x in d.tezgah_duruslari.values() if x['tezgah']==tezgah]+[(x['baslangic'],x['bitis'] or d.saat.simdi(),x['neden']) for x in d.duruslar.values() if birim_kapsamda(d,b,x['kapsam'])]


def tezgah_uygun_mu(d,tezgah,bas,bit):
    a,b=an(bas),an(bit)
    if tezgah not in d.tezgahlar or a>=b: raise ValueError('Tezgah/aralik')
    for x in d.bakimlar.values():
        if x['tezgah']==tezgah and not x['iptal'] and kesisim(a,b,an(x['baslangic']),an(x['bitis'])): return dict(uygun=False,neden='bakim')
    if any(kesisim(a,b,p,q) for p,q,_ in tezgah_engelleri(d,tezgah)): return dict(uygun=False,neden='durus')
    dis=cikar([(a,b)],tezgah_planli_araliklar(d,tezgah,a,b))
    return dict(uygun=not dis,neden='vardiya disi' if dis else None)


def tezgah_gostergesi(d,tezgah,bas,bit):
    from .gorunum_v10_1 import pencere
    a,b=pencere(bas,bit)
    payda=saatler(tezgah_planli_araliklar(d,tezgah,a,b)); nedenler=defaultdict(list)
    for p,q,n in tezgah_engelleri(d,tezgah):
        if kesisim(a,b,p,q): nedenler[n].append((max(a,p),min(b,q)))
    gercek=saatler([(max(a,x['baslangic']),min(b,x['bitis'] or d.saat.simdi())) for x in d.araliklar if x['tezgah']==tezgah and x['kova']=='TEZGAH' and max(a,x['baslangic'])<min(b,x['bitis'] or d.saat.simdi())])
    bekleme=sum((min(b,x['bitis_ani'])-max(a,x['makine_bitis_ani'])).total_seconds()/60 for x in d.isler.values() if x.get('tezgah')==tezgah and x.get('makine_bitis_ani') and max(a,x['makine_bitis_ani'])<min(b,x['bitis_ani']))
    return dict(bitti_alinmayi_bekledi_dk=bekleme,planli_kullanilabilir=payda,gerceklesen=gercek,durus={n:saatler(v) for n,v in nedenler.items()},kullanim_orani=gercek/payda if payda else None)


def sorumluluk_performansi(d,kisi,bas,bit,tur='KISI'):
    from .gorev import son_teslim_ani
    kalite=0.0; gecikme=0.0
    for x in d.sorumluluklar.values():
        if x.get('kaynak_turu') in ('GECIKME','DEGISIKLIK') or x['tur']!=tur or x['kimlik']!=kisi or not x['dogrulandi'] or x['itirazda']: continue
        if gun(bas)<=gun(an(x['an']))<=gun(bit): kalite+=x['yuzde']/100
        for h in x['hedef']:
            g=d.gorevler.get(h['kimlik'],{})
            if g.get('durum')=='BITTI' and g.get('bitis_ani') and gun(bas)<=gun(an(g['bitis_ani']))<=gun(bit) and son_teslim_ani(g,d) and an(g['bitis_ani'])>son_teslim_ani(g,d):
                ret=next((r for r in d.retler if r['olay']==x['ret']),{})
                gecikme+=ret.get('zaman_degeri',g['zaman_degeri'])*x['yuzde']/100
    from .gorunum_v9 import sorumluluk_ekleri
    ek=sorumluluk_ekleri(d,kisi,bas,bit,tur)
    return dict(kalite_ret=kalite+ek['kalite_ret'],sebep_olunan_gecikme=gecikme+ek['sebep_olunan_gecikme'])


def gun_ozeti(d,kisi,tarih):
    tarih=str(gun(tarih)); kovalar=defaultdict(float); isler=defaultdict(float)
    for x in d.araliklar:
        if x['kisi']!=kisi or str(x['gun'])!=tarih: continue
        dakika=((x['bitis'] or d.saat.simdi())-x['baslangic']).total_seconds()/60
        kovalar[x['kova']]+=dakika
        if x['is'] and x['kova'] in ('CALISMA','YENIDEN_ISLEME'): isler[x['is']]+=dakika
    gorevler={k:{a:v.get(a) for a in ('durum','kabul_ani','teslim_ani','bitis_ani')} for k,v in d.gorevler.items() if v['kisi']==kisi and gun(an(v['atama_ani']))<=gun(tarih) and (not v.get('bitis_ani') or gun(an(v['bitis_ani']))>=gun(tarih))}
    notlar=[k for k,v in d.notlar.items() if v['yazan']==kisi and str(gun(an(v['an'])))==tarih]
    # Parasal tutar ozetin paylasilabilir bolumune girmez.
    fm=[{k:v for k,v in x.items() if k not in ('prim',)} for x in fazla_mesai_kayitlari(d) if x['kisi']==kisi and x['tarih']==tarih]
    return dict(kovalar=dict(kovalar),isler=dict(isler),gorevler=gorevler,notlar=notlar,fazla_mesai=fm)


def ozet_surumu(ozet): return sha256(kodla(ozet).encode('utf-8')).hexdigest()


def gun_sonu_raporu(d,kisi,tarih):
    key=kisi+':'+str(gun(tarih)); ay=str(gun(tarih).replace(day=1))
    kapanis=getattr(d,'ay_kapanislari',{}).get(ay+':RAPORLAR',{})
    if key in kapanis: return deepcopy(kapanis[key])
    r=deepcopy(d.gun_sonu_raporlari.get(key,dict(kisi=kisi,gun=str(gun(tarih)),durum='TASLAK')))
    r['ozet']=gun_ozeti(d,kisi,tarih); r['ozet_surumu']=ozet_surumu(r['ozet'])
    if r.get('onaylanan_ozet_surumu'):
        if r['durum']=='ONAYLANDI' and r['onaylanan_ozet_surumu']!=r['ozet_surumu']: r['durum']='DEGISTI'
        kaynak=d.olaylar.values() if hasattr(d.olaylar,'values') else d.olaylar
        bilinen=[e for e in kaynak if an(e['oldugu_an'])<=r['onay_ani'] and an(e.get('bulut_ulasma_ani',e['oldugu_an']))<=r['onay_ani']]
        # Degismez olaylarin ayni kumesinden ayni onay fotografini tekrar kurma.
        # Bu gecici onbellek kaynak/son_hal/para hesabinin parcasi degildir.
        anahtar=(kisi,str(tarih),r['onaylanan_ozet_surumu'],tuple(sorted(e['olay_kimligi'] for e in bilinen)))
        onbellek=getattr(d,'_rapor_onay_onbellegi',None)
        if onbellek is None: onbellek={}; d._rapor_onay_onbellegi=onbellek
        if anahtar not in onbellek:
            from .motor import Motor
            m=Motor(Saat(r['onay_ani'])); m.yurut(bilinen); m.hassas_ekler=[]
            onbellek[anahtar]=gun_ozeti(m,kisi,tarih)
        r['onaylanan_ozet']=deepcopy(onbellek[anahtar])
    from .gorunum_v9 import gun_onayi_gerekli
    r['onay_durumu']=r['durum'] if gun_onayi_gerekli(d,kisi,tarih) or r['durum']=='ONAYLANDI' else 'ONAY_GEREKMIYOR'
    return r


def eski_hatirlatmalar(d):
    if not d.ayar('gun_sonu_raporu_zorunlu',d.saat.simdi(),False): return []
    sonuc=[]
    for kisi,p in d.kisiler.items():
        for tarih in gunler(p['giris_tarihi'],d.saat.simdi().date()-timedelta(days=1)):
            if not d.is_gunu(tarih) or not istihdamda(d,kisi,tarih): continue
            sonraki=tarih+timedelta(days=1)
            for _ in range(370):
                if d.is_gunu(sonraki): break
                sonraki+=timedelta(days=1)
            esik=saat_ani(sonraki,d.takvim(sonraki)['mesai_baslangic'])
            ayar=d.ayar('gun_sonu_hatirlatma',d.saat.simdi(),'ERTESI_IS_GUNU')
            if type(ayar) in (int,float): esik+=timedelta(hours=ayar)
            if d.saat.simdi()<esik: continue
            r=gun_sonu_raporu(d,kisi,tarih)
            kod='R32' if r['durum']=='TASLAK' else 'R33' if r['durum'] in ('GONDERILDI','DEGISTI') else None
            if kod:
                for alici in sorted(ustler(d,kisi)|({kisi} if kod=='R32' else set())):
                    sonuc.append(dict(kural=kod,alici=alici,kisi=kisi,gun=str(tarih),an=esik))
    return sonuc


def hatirlatmalar(d):
    from .gorunum_v9 import hatirlatmalar as v9
    return v9(d)


def plan_karsilastir(d,proje):
    ss=deepcopy(d.plan_surumleri.get(proje,[]))
    guncel={k:{a:v[a] for a in ('ad','birim','baslangic','bitis','hedef_saat')} for k,v in d.etaplar.items() if v['proje']==proje}
    b0=ss[0]['etaplar'] if ss else {}; son=ss[-1]['etaplar'] if ss else {}
    from .gorunumler import etap_gostergesi
    return dict(B0=b0,son_onayli=son,guncel=guncel,onaysiz_degisti=bool(ss) and guncel!=son,
                sapma={k:dict(bitis_gun=(gun(v['bitis'])-gun(b0[k]['bitis'])).days,hedef_saat=v['hedef_saat']-b0[k]['hedef_saat']) for k,v in guncel.items() if k in b0},
                gerceklesen={k:etap_gostergesi(d,k) for k in guncel})


def top_kimde(d,kimlik):
    x=d.nesneler[kimlik]; sureler=defaultdict(float)
    for s in x['asama_gecmisi']: sureler[s['asama']]+=(s['bitis']-s['baslangic']).total_seconds()/60
    sureler[x['asama']]+=(d.saat.simdi()-x['asama_ani']).total_seconds()/60
    return dict(asama=x['asama'],sorumlu=x['sorumlu'],asama_ani=x['asama_ani'],asama_dakikalari=dict(sureler))


def durum(d,t):
    from .depo import Depo
    t=an(t); z=Depo(Saat(t),'tam')
    z._kayitlar={k:deepcopy(e) for k,e in d.olaylar.items() if an(e['oldugu_an'])<=t and an(e['bulut_ulasma_ani'])<=t}
    z.hassas_ekler=[deepcopy(x) for x in d.hassas_ekler if x['olay'] in z._kayitlar]
    kapali={k[:10] for k,v in d.ay_kapanislari.items() if isinstance(v,dict) and 'kapanis_ani' in v and an(v['kapanis_ani'])<=t}
    z.ay_kapanislari={k:deepcopy(v) for k,v in d.ay_kapanislari.items() if k[:10] in kapali}
    z.yeniden_kur(); return z


def gecmis_gorunumu(d,t):
    z=durum(d,t)
    return {k:deepcopy(getattr(z,k)) for k in ('kisi_durumu','listeler','isler','gorevler','araliklar','ay_kapanislari')}


def donem_defteri(d,bas,bit):
    """Yuvarlama gruplamada bir kez; duzeltme canli eksi donuk defterdir."""
    from .gorunumler import para,gorev_payi
    z=copy(d); z.ay_kapanislari={}
    sonuc=defaultdict(lambda:dict(saat=0.0,tutar=Decimal(0)))
    def ekle(proje,kisi,kalem,saat,oran):
        x=sonuc[(proje or 'BELIRSIZ',kisi,kalem)]; x['saat']+=saat
        if oran==EKSIK or x['tutar']==EKSIK: x['tutar']=EKSIK
        else: x['tutar']+=Decimal(str(saat))*oran
    for x in d.araliklar:
        if not x['kisi'] or not gun(bas)<=x['gun']<=gun(bit) or x['kova'] not in ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY'): continue
        ekle(x['proje'] or x['kategori'],x['kisi'],'ISCILIK',((x['bitis'] or d.saat.simdi())-x['baslangic']).total_seconds()/3600,saat_maliyeti(d,x['kisi'],x['gun']))
    for g in d.gorevler.values():
        for tarih in gunler(bas,bit):
            for k in {g['kisi']}|{x['kisi'] for x in g.get('kisi_gecmisi',[])}:
                pay=gorev_payi(z,g,tarih,tarih,kisi=k)
                if pay: ekle(g.get('proje') or g.get('kategori'),k,'MAAS',pay,saat_maliyeti(d,k,tarih))
    for x in fazla_mesai_kayitlari(d):
        if gun(bas)<=gun(x['tarih'])<=gun(bit):
            oran=saat_maliyeti(d,x['kisi'],x['tarih'])
            ekle(x['proje'] or x['kategori'],x['kisi'],'FAZLA_MESAI_PRIMI',x['saat'],EKSIK if oran==EKSIK else oran*Decimal(str(x['katsayi']-1)))
    return {'|'.join(k):dict(v,proje=k[0],kisi=k[1],kaynak_kalem=k[2],tutar=EKSIK if v['tutar']==EKSIK else para(v['tutar'])) for k,v in sorted(sonuc.items())}


def onceki_donem_duzeltmeleri(d):
    from .gorunumler import ay_sinirlari,para
    sonuc=[]; kapali=sorted(k[:10] for k in d.ay_kapanislari if k.endswith(':DEFTER_V7'))
    for ay in kapali:
        a,b=ay_sinirlari(ay); yeni=duzeltme_defteri(d,ay); eski=d.ay_kapanislari[ay+':DEFTER_V7']
        hedef=(b+timedelta(days=1)).replace(day=1)
        while str(hedef) in kapali: hedef=(hedef.replace(day=28)+timedelta(days=4)).replace(day=1)
        for key in sorted(set(yeni)|set(eski)):
            x=yeni.get(key,dict(saat=0,tutar=Decimal(0))); y=eski.get(key,dict(saat=0,tutar=Decimal(0)))
            # Ayni eksik veri fotografi, tek basina yeni bir mali hareket degildir.
            once_yazilan=[v for donem in kapali for v in d.ay_kapanislari.get(donem+':DUZELTMELER',[]) if v['kaynak_ay']==ay and v['anahtar']==key]
            if x==y and not once_yazilan: continue
            tutar=EKSIK if EKSIK in (x['tutar'],y['tutar']) else x['tutar']-y['tutar']; saat=x['saat']-y['saat']
            for donem in kapali:
                for once in d.ay_kapanislari.get(donem+':DUZELTMELER',[]):
                    if once['kaynak_ay']==ay and once['anahtar']==key:
                        if tutar!=EKSIK and once['tutar']!=EKSIK: tutar-=once['tutar']
                        saat-=once['saat']
            if abs(saat)<1e-9 and tutar==0: continue
            p,k,kalem=key.split('|')
            sonuc.append(dict(anahtar=key,kalem='ONCEKI_DONEM_DUZELTMESI',kaynak_kalem=kalem,proje=p,kisi=k,kaynak_ay=ay,ay=str(hedef),saat=saat,tutar=tutar if tutar==EKSIK else para(tutar)))
    return sonuc


def duzeltme_defteri(d,ay):
    """Kapanista bilinenler + eski doneme ait gec taniklik/izli duzeltme.

    Sonraki aya verilen tatil eski ayin payini yeniden dagitmaz (karar 50).
    """
    from .gorunumler import ay_sinirlari
    from .depo import Depo
    a,b=ay_sinirlari(ay)
    kapanis=next(v['kapanis_ani'] for k,v in d.ay_kapanislari.items() if k.startswith(ay+':') and isinstance(v,dict) and 'kapanis_ani' in v)
    es=list(d.olaylar.values()); kabul={e['olay_kimligi'] for e in es if an(e['bulut_ulasma_ani'])<=kapanis}
    for e in es:
        g=e['girdiler']; zaman=an(e['oldugu_an'])
        if zaman.date()<=b: kabul.add(e['olay_kimligi'])
        if e['eylem_kodu'] in ('IS.SURE_EKLEDIM','EK_MESAI.ONAYLADIM','IZIN.TALEP_ETTIM'):
            tarih=gun(g['tarih']) if g.get('tarih') else an(g['baslangic']).date()
            if tarih<=b: kabul.add(e['olay_kimligi'])
    for e in es:
        if e['eylem_kodu'] in ('KAYIT.GECERSIZ_SAYDIM','IZIN.ONAYLADIM','IZIN.IK_ONAYLADIM','IZIN.IPTAL_ETTIM') and e['girdiler'].get('hedef') in kabul: kabul.add(e['olay_kimligi'])
    z=Depo(d.saat,'tam'); z._kayitlar={e['olay_kimligi']:deepcopy(e) for e in es if e['olay_kimligi'] in kabul}
    z.hassas_ekler=deepcopy(d.hassas_ekler); z.yeniden_kur()
    return donem_defteri(z,a,b)


def kapanis_ekleri(d,bas,bit):
    from .gorunum_v9 import onay_uyarilari
    ay=str(bas)
    cihazlar={k:x['son_esitleme'] for k,x in d.cihaz_esitlemeleri.items()}
    for e in d.olaylar.values(): cihazlar[e['cihaz']]=max(cihazlar.get(e['cihaz'],an(e['bulut_ulasma_ani'])),an(e['bulut_ulasma_ani']))
    return {ay+':DEFTER_V7':donem_defteri(d,bas,bit),
            ay+':RAPORLAR':{k:gun_sonu_raporu(d,x['kisi'],x['gun']) for k,x in d.gun_sonu_raporlari.items() if bas<=gun(x['gun'])<=bit},
            ay+':DUZELTMELER':[x for x in onceki_donem_duzeltmeleri(d) if x['ay']==ay],
            ay+':ONAY_UYARILARI':onay_uyarilari(d,bas,bit),
            ay+':CIHAZ_UYARILARI':{k:v for k,v in cihazlar.items() if v<d.saat.simdi()}}


def oku(d,kim,veri,hedef=None,**g):
    """Dis modulun tek okuma kapisi; ham ic sorgular servis icindir."""
    from . import gorunum_v10_1 as t10
    from . import gorunum_v10_2 as t11
    if veri not in t11.YENI_VERILER | t11.ESKI_VERILER: raise ValueError('TANIMSIZ_VERI')
    if veri in t11.YENI_VERILER: return t11.oku(d,kim,veri,hedef,**g)
    if veri == 'GANTT': return t10.gantt(d,hedef,g['bas'],g.get('bit'),cagiran=kim)
    if veri == 'PLAN_CAKISMALARI': return t10.plan_cakismalari(d,hedef,g['bas'],g.get('bit'),cagiran=kim)
    if veri == 'SURUMLER': return t10.surumler(d,hedef,cagiran=kim)
    if veri == 'GECERLI_SURUM': return t10.gecerli_surum(d,hedef,g.get('t'),cagiran=kim)
    if veri == 'BILDIRIMLER': return t10.bildirim_kutusu(d,hedef,cagiran=kim)
    if not gorebilir_mi(d,kim,veri,hedef): raise PermissionError('Gorunurluk')
    from .gorunumler import adil_performans,proje_gostergesi,etap_gostergesi
    if veri in ('PROJE','ETAP','NOT','DOSYA'):
        return deepcopy({'PROJE':d.projeler,'ETAP':d.etaplar,'NOT':d.notlar,'DOSYA':d.dosyalar}[veri].get(hedef))
    if veri=='PLAN': return plan_karsilastir(d,hedef)
    if veri in ('KIM_NEREDE','SAAT_NEREYE_GITTI'):
        from .gorunumler import kim_nerede,saat_nereye_gitti
        return (kim_nerede if veri=='KIM_NEREDE' else saat_nereye_gitti)(d,g['bas'],g['bit'],cagiran=kim)
    if veri=='PERFORMANS': return adil_performans(d,hedef,g['bas'],g['bit'],kim)
    if veri=='GUN':
        r=gun_sonu_raporu(d,hedef,g['gun']); r.pop('gecmis',None); return r
    if veri=='MAAS': return aylik_maliyet_ozeti(d,hedef,g['ay'])
    if veri=='SAAT_MALIYETI': return saat_maliyeti(d,hedef,g['gun'])
    if veri in ('IZIN','IZIN_DETAY'): return [deepcopy(x) for x in d.izinler.values() if x['kisi']==hedef]
    if veri=='HAM_OLAY': return [deepcopy(x) for x in d.olaylar.values() if (x['kim']==hedef or 'YETKILI' in d.kisiler[kim]['roller']) and t10.surum_olayi_gorebilir(d,kim,x)]
    if veri=='FAZLA_MESAI': return [{k:v for k,v in x.items() if k!='prim' or gorebilir_mi(d,kim,'TUTAR')} for x in fazla_mesai_kayitlari(d) if x['kisi']==hedef]
    if veri=='NESNE': return deepcopy(d.nesneler.get(hedef))
    if veri=='UYGUNLUK': return kisi_uygun_mu(d,hedef,g['bas'],g['bit'],kim)
    if veri=='BIRIM_PERFORMANS':
        kisiler=[k for k,p in d.kisiler.items() if p['birim']==hedef]
        sonuc={a:sum(adil_performans(d,k,g['bas'],g['bit'])[a] for k in kisiler) for a in ('teslim','zamaninda','kalite_ret','sebep_olunan_gecikme')}
        for a,v in sorumluluk_performansi(d,hedef,g['bas'],g['bit'],'BIRIM').items(): sonuc[a]+=v
        return sonuc
    if veri in ('PROJE_DURUM','ETAP_DURUM'):
        sonuc=proje_gostergesi(d,hedef,cagiran=kim) if veri=='PROJE_DURUM' else etap_gostergesi(d,hedef)
        if not gorebilir_mi(d,kim,'TUTAR'):
            def ayikla(x):
                if isinstance(x,dict): return {k:ayikla(v) for k,v in x.items() if k not in ('maliyet','iscilik','tezgah','maas','tutar','tutarlar','prim')}
                if isinstance(x,list): return [ayikla(v) for v in x]
                return x
            sonuc=ayikla(sonuc)
        return sonuc
    if veri in ('GOREV','IS'):
        tablo=d.gorevler if veri=='GOREV' else d.isler
        if hedef in tablo: return deepcopy(tablo[hedef])
        return [deepcopy(x) for x in tablo.values() if x.get('kisi')==hedef and gorebilir_mi(d,kim,veri,x['kimlik'])]
    raise ValueError('Tanimli gorunum gerekli')


def modul_yaz(d,kim,olay):
    if olay['kim']!=kim or olay['giris_sekli']=='AKTARIM': return d.red('YETKI','Modul kullanici oturumu')
    return d.olay_ekle(olay,oturum=kim)
