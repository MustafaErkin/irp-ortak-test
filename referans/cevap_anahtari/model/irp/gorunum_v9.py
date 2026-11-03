"""T9 okumalar: proje erisimi, gecikme, degisiklik ve gun onayi."""
from collections import defaultdict
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from .saat import an, gun, gun_ani
from .yetki_v6 import ustler, yoneticiler, birim_ustleri, istihdamda
from .kurallar_v9 import olaylar, tablo_izni, gecikme_hedefi, neden_satiri
from .takvim_v7 import gunler, normal, kisi_normal, saatler
from .takvim_v9 import kisi_birimi


def proje_kaydi(d,proje,t=None,cagiran=None):
    if t is not None:
        from .gorunum_v7 import durum
        d=durum(d,t)
    if cagiran and not proje_gorebilir_mi(d,cagiran,proje): raise PermissionError('Proje gorunurlugu')
    return deepcopy(d.projeler.get(proje))


def proje_uyeleri(d,proje,t=None):
    if t is not None:
        from .gorunum_v7 import durum
        return proje_uyeleri(durum(d,t),proje)
    sonuc=set(); birimler=set()
    for x in list(d.isler.values())+list(d.gorevler.values()):
        if x.get('proje') != proje: continue
        sonuc.update(x.get(a) for a in ('kisi','atayan','veren','onaylayan'))
        sonuc.update(s.get('kisi') for s in x.get('kisi_gecmisi',[]))
        if x.get('birim'): birimler.add(x['birim'])
    birimler.update(x['birim'] for x in d.etaplar.values() if x['proje']==proje)
    sonuc.add(d.projeler.get(proje,{}).get('sorumlu'))
    # Etkin olaylarin eski kisi/atayan/onaylayan ve proje sorumlusu baglari kalir.
    baglar={}; sahipler={}
    for e in sorted(olaylar(d),key=lambda x:(x['oldugu_an'],x['olay_kimligi'])):
        kod,g,oid=e['eylem_kodu'],e['girdiler'],e['olay_kimligi']
        if an(e['oldugu_an']) > d.saat.simdi(): continue
        if kod=='PROJE.ACTIM' and g.get('kimlik',g['kod'])==proje: sonuc.add(g.get('sorumlu'))
        if kod=='PROJE.DEGISTIRDIM' and any(h['tur']=='PROJE' and h['kimlik']==proje for h in e['neyin_ustunde']): sonuc.add(g['degisenler'].get('sorumlu'))
        if kod in ('GOREV.ATADIM','IS.TANIMLADIM','IS.PLANSIZ_TANIMLADIM'):
            ss=g.get('gorevler',g.get('isler',[g]))
            for n,s in enumerate(ss,1):
                key=oid+'/'+str(n) if kod.startswith('GOREV') or len(ss)>1 else oid
                baglar[key]=s.get('proje'); sahipler[key]={e['kim'],s.get('kisi'),s.get('onaylayan')}
                if s.get('proje')==proje:
                    sonuc.update(sahipler[key])
                    if s.get('birim'): birimler.add(s['birim'])
        for h in e['neyin_ustunde']:
            key=h['kimlik']
            if h['tur'] not in ('IS','GOREV'): continue
            if kod in ('IS.BAGLANTI_DUZELTTIM','GOREV.DEGISTIRDIM') and 'proje' in g['degisenler']: baglar[key]=g['degisenler']['proje']
            if kod in ('IS.ATADIM','IS.DEVRETTIM','GOREV.DEGISTIRDIM','IS.ONAYLADIM','GOREV.ONAYLADIM'):
                s=g.get('degisenler',g)
                sahipler.setdefault(key,set()).update({e['kim'],s.get('kisi'),s.get('kime'),s.get('onaylayan')} | set(s.get('kisiler',[])))
            if baglar.get(key)==proje: sonuc.update(sahipler.get(key,set()))
    for b in birimler: sonuc.update(yoneticiler(d,b))
    kisiler={}
    for e in sorted(olaylar(d),key=lambda x:(an(x['girdiler'].get('gecerli_baslangic',x['oldugu_an'])),x['olay_kimligi'])):
        g=e['girdiler']; kod=e['eylem_kodu']
        if an(g.get('gecerli_baslangic',e['oldugu_an']))>d.saat.simdi(): continue
        if kod=='BIRIM.TANIMLADIM' and g['kod'] in birimler: sonuc.add(g.get('basi'))
        if kod=='KISI.EKLEDIM': kisiler[g['kod']]=deepcopy(g)
        if kod=='KISI.DEGISTIRDIM' and g['kisi'] in kisiler: kisiler[g['kisi']].update(g['degisenler'])
        k=g.get('kod') if kod=='KISI.EKLEDIM' else g.get('kisi') if kod=='KISI.DEGISTIRDIM' else None
        p=kisiler.get(k,{})
        if p.get('birim') in birimler and 'EKIP_LIDERI' in p.get('roller',[]): sonuc.add(k)
    erisim={}
    for x in sorted(d.proje_erisimleri.values(),key=lambda x:(x['an'],x['kimlik'])):
        if x['proje']==proje: erisim[x['kisi']]=x['acik']
    sonuc.update(k for k,v in erisim.items() if v)
    return sonuc-{None}


def proje_gorebilir_mi(d,kim,proje,t=None):
    if t is not None:
        from .gorunum_v7 import durum
        return proje_gorebilir_mi(durum(d,t),kim,proje)
    if proje not in d.projeler or not istihdamda(d,kim,d.saat.simdi()): return False
    if d.ayar('proje_gorunurlugu',d.saat.simdi(),'HERKES')=='HERKES': return True
    from .kurallar_v10 import projede_yetkili
    if projede_yetkili(d,kim,proje): return True
    def uye(p):
        if projede_yetkili(d,kim,p): return True
        uyeler=proje_uyeleri(d,p)
        return kim in uyeler or any(kim in ustler(d,k) for k in uyeler)
    komsular={proje}|{k for k,p in d.projeler.items() if p.get('ana_proje')==proje}
    if d.projeler[proje].get('ana_proje'): komsular.add(d.projeler[proje]['ana_proje'])
    return any(uye(p) for p in komsular)


def projesi(d,veri,hedef):
    if veri in ('PROJE','PROJE_DURUM','PROJE_TUTAR','MALIYET','PLAN'): return hedef if hedef in d.projeler else None
    tablo={'IS':d.isler,'GOREV':d.gorevler,'ETAP':d.etaplar,'ETAP_DURUM':d.etaplar,'NESNE':d.nesneler,'NOT':d.notlar,'DOSYA':d.dosyalar}.get(veri,{})
    x=tablo.get(hedef,{})
    if veri=='NOT':
        for h in x.get('neyin_ustunde',[]):
            p=projesi(d,h['tur'],h['kimlik'])
            if p: return p
    if veri=='DOSYA':
        e=next((e for e in olaylar(d) if e['olay_kimligi']==x.get('doguran_olay')), {})
        for h in e.get('neyin_ustunde',[]):
            p=projesi(d,h['tur'],h['kimlik'])
            if p: return p
        for y in list(d.gorevler.values())+list(d.isler.values()):
            if y.get('doguran_olay')==x.get('doguran_olay'): return y.get('proje')
    return x.get('proje')


def bagli_projeler(d,veri,hedef,gezilen=None):
    """Cok hedefli not/dosya butun baglarin okuma kapisindan gecer."""
    gezilen=set() if gezilen is None else gezilen
    if (veri,hedef) in gezilen: return set()
    gezilen.add((veri,hedef))
    if veri=='NOT': hs=d.notlar.get(hedef,{}).get('neyin_ustunde',[])
    elif veri=='DOSYA':
        oid=d.dosyalar.get(hedef,{}).get('doguran_olay')
        e=next((e for e in olaylar(d) if e['olay_kimligi']==oid),{})
        hs=e.get('neyin_ustunde',[])
        hs=hs+[dict(tur='NOT',kimlik=oid)] if oid in d.notlar else hs
        hs=hs+[dict(tur=tur,kimlik=k) for tur,tablo in [('IS',d.isler),('GOREV',d.gorevler)] for k,x in tablo.items() if x.get('doguran_olay')==oid]
    else:
        p=projesi(d,veri,hedef)
        return {p} if p else set()
    sonuc=set()
    for h in hs: sonuc.update(bagli_projeler(d,h['tur'],h['kimlik'],gezilen))
    return sonuc


def gorebilir_mi(d,kim,veri,hedef=None):
    if veri == 'DOSYA':
        from .gorunum_v10_1 import dosya_gorebilir
        if not dosya_gorebilir(d,kim,hedef): return False
    from .gorunum_v7 import temel_gorebilir_mi
    aliases={'ADIL_PERFORMANS':'PERFORMANS','PROJE':'PROJE_DURUM','ETAP':'ETAP_DURUM','PLAN':'PROJE_DURUM','NOT':'PROJE_DURUM','DOSYA':'PROJE_DURUM','KIM_NEREDE':'UYGUNLUK','SAAT_NEREYE_GITTI':'UYGUNLUK'}
    tur=aliases.get(veri,veri); k=hedef
    if veri in ('IS','GOREV') and hedef not in d.kisiler:
        x=(d.isler if veri=='IS' else d.gorevler).get(hedef,{})
        if not x: return False
        k=x.get('kisi')
        # Havuz satirinin kisisel sonucu yok; proje kapiyla okunur.
        if not k: tur='PROJE_DURUM'
    if not temel_gorebilir_mi(d,kim,tur,k): return False
    return all(proje_gorebilir_mi(d,kim,p) for p in bagli_projeler(d,veri,hedef))


def pano_projeleri(d,paylar,cagiran):
    sonuc=defaultdict(float)
    for p,pay in paylar.items():
        ad='erişim dışı proje' if p in d.projeler and not proje_gorebilir_mi(d,cagiran,p) else p
        sonuc[ad]+=pay
    return dict(sonuc)


def proje_erisim_gecmisi(d,proje,cagiran=None):
    if cagiran and not proje_gorebilir_mi(d,cagiran,proje): raise PermissionError('Proje gorunurlugu')
    sonuc=[deepcopy(x) for x in d.proje_erisimleri.values() if x['proje']==proje]
    for e in olaylar(d):
        if e['eylem_kodu'] not in ('ETAP.TANIMLADIM','ETAP.DEGISTIRDIM'): continue
        g=e['girdiler']; hedef=e['olay_kimligi'] if e['eylem_kodu']=='ETAP.TANIMLADIM' else next(h['kimlik'] for h in e['neyin_ustunde'] if h['tur']=='ETAP')
        if d.etaplar.get(hedef,{}).get('proje')==proje:
            sonuc.append(dict(kimlik=e['olay_kimligi'],an=an(e['oldugu_an']),yazan=e['kim'],proje=proje,etap=hedef,eylem=e['eylem_kodu'],girdiler=deepcopy(g)))
    return sorted(sonuc,key=lambda x:(x['an'],x['kimlik']))


def okunmamis_bildirimler(d,kisi):
    from .modul_bildirimi import kutu
    return [s for s in kutu(d,kisi) if not s.get('gorulme_ani')]


def son_degerlendirme(d,hedef):
    es=[x for x in d.gecikme_degerlendirmeleri.values() if x['hedef']==hedef]
    return max(es,key=lambda x:(x['an'],x['kimlik'])) if es else None


def zaman_katkisi(d,g):
    from .gorev import son_teslim_ani
    if an(g['ilk_teslim_ani'])<=son_teslim_ani(g,d): return 1.0
    from .kurallar_v10 import kredi
    return kredi(d,g)


def gecikme_satirlari(d,bas,bit):
    adaylar={k for k,g in d.gorevler.items() if g.get('ilk_teslim_ani')}
    adaylar.update(e['olay_kimligi'] for e in olaylar(d) if e['eylem_kodu']=='IS.ARIZA_BILDIRDIM')
    sonuc=[]
    for hedef in sorted(adaylar):
        h=gecikme_hedefi(d,hedef)
        if not h or not gun(bas)<=gun(an(h['an']))<=gun(bit): continue
        ev=son_degerlendirme(d,hedef)
        if h['tur']=='GOREV': neden=d.gorevler[hedef].get('gecikme_nedeni') or 'GIRILMEDI'
        else: neden=next(e['girdiler'].get('neden') or 'BELIRTILMEDI' for e in olaylar(d) if e['olay_kimligi']==hedef)
        neden=ev['neden'] if ev else neden
        baslik=neden_satiri(d,neden).get('ust') or ('ESKI_ARIZA' if str(neden).startswith('ARIZA.') else 'GIRILMEDI')
        dakika=sum(((a['bitis'] or d.saat.simdi())-a['baslangic']).total_seconds()/60 for a in d.araliklar if a['kova']=='BEKLEME_ARIZA' and a.get('acan_olay')==hedef)
        ss=[x for x in d.sorumluluklar.values() if ev and x['ret']==ev['kimlik']]
        if not ss: ss=[dict(tur='KISI',kimlik=h['kisi'],yuzde=100,dogrulandi=False,itirazda=False)]
        from .gorunum_v10_2 import gecikme_olculeri
        olcu=gecikme_olculeri(d,'GOREV',d.gorevler[hedef]) if h['tur']=='GOREV' else dict(gecikme_takvim_dk=0,gecikme_mesai_dk=0)
        for x in ss:
            from .kurallar_v10 import etkin_pay
            x=dict(x,dogrulandi=etkin_pay(d,x))
            pay=x['yuzde']/100
            sonuc.append(dict(hedef=hedef,**h,neden=neden,baslik=baslik,sorumlu_turu=x['tur'],sorumlu=x['kimlik'],yuzde=x['yuzde'],degerlendirildi=bool(ev),dogrulandi=x['dogrulandi'],itirazda=x['itirazda'],
                durus_dk=dakika*pay,gec_teslim=pay if h['tur']=='GOREV' else 0,gecikme_saati=h['zaman_degeri']*pay,
                **{alan:(deger or 0)*pay for alan,deger in olcu.items()},
                sebep_olunan_bekleme_dk=dakika*pay if x['dogrulandi'] and not x['itirazda'] else 0,
                sebep_olunan_gecikme=h['zaman_degeri']*pay if x['dogrulandi'] and not x['itirazda'] and x['kimlik']!=h['kisi'] else 0))
    return sonuc


def gecikme_raporu(d,bas,bit,kirilim='sorumlu',cagiran=None):
    if kirilim not in ('baslik','neden','sorumlu','proje','birim','kisi'): raise ValueError('Gecikme kirilimi')
    sonuc={}
    for x in gecikme_satirlari(d,bas,bit):
        if cagiran:
            if x['sorumlu_turu']=='KISI': izin=gorebilir_mi(d,cagiran,'PERFORMANS',x['sorumlu'])
            else: izin=gorebilir_mi(d,cagiran,'BIRIM_PERFORMANS',x['birim'])
            if not izin or (x['proje'] and not proje_gorebilir_mi(d,cagiran,x['proje'])): continue
        kimlik=(x['sorumlu_turu']+':'+x['sorumlu']) if kirilim=='sorumlu' else x[kirilim]
        k=(kimlik,x['degerlendirildi'],x['dogrulandi'],x['itirazda'],x['neden'])
        r=sonuc.setdefault(k,dict(kimlik=kimlik,degerlendirildi=x['degerlendirildi'],dogrulandi=x['dogrulandi'],itirazda=x['itirazda'],neden=x['neden'],durus_dk=0,gec_teslim=0,zaman_degeri=0,sebep_olunan_bekleme_dk=0,sebep_olunan_gecikme=0,gecikme_takvim_dk=0,gecikme_mesai_dk=0))
        for a in ('durus_dk','gec_teslim','sebep_olunan_bekleme_dk','sebep_olunan_gecikme','gecikme_takvim_dk','gecikme_mesai_dk'): r[a]+=x[a]
        r['zaman_degeri']+=x['gecikme_saati']
    return list(sonuc.values())


def sorumluluk_ekleri(d,kisi,bas,bit,tur='KISI'):
    if not d.gecikme_degerlendirmeleri and not any(x.get('kaynak_turu')=='DEGISIKLIK' for x in d.sorumluluklar.values()):
        return dict(kalite_ret=0,sebep_olunan_gecikme=0,sebep_olunan_bekleme_dk=0)
    kalite=sum(x['yuzde']/100 for x in d.sorumluluklar.values() if x.get('kaynak_turu')=='DEGISIKLIK' and x['tur']==tur and x['kimlik']==kisi and x['dogrulandi'] and not x['itirazda'] and gun(bas)<=gun(an(x['an']))<=gun(bit))
    ss=[x for x in gecikme_satirlari(d,bas,bit) if x['sorumlu_turu']==tur and x['sorumlu']==kisi]
    return dict(kalite_ret=kalite,sebep_olunan_gecikme=sum(x['sebep_olunan_gecikme'] for x in ss),sebep_olunan_bekleme_dk=sum(x['sebep_olunan_bekleme_dk'] for x in ss))


def degisiklik_gecmisi(d,kaynak,cagiran=None):
    tablo=dict(d.isler,**d.gorevler)
    if kaynak not in tablo: raise ValueError('Kaynak yok')
    p=tablo[kaynak].get('proje')
    if cagiran and p and not proje_gorebilir_mi(d,cagiran,p): raise PermissionError('Proje gorunurlugu')
    sonuc=[]
    def gez(k):
        if k in sonuc: return
        sonuc.append(k)
        for x in sorted(tablo.values(),key=lambda x:x['kimlik']):
            if x.get('degisiklik_kaynagi')==k: gez(x['kimlik'])
    gez(kaynak)
    return sonuc


def proje_degisiklikleri(d,proje,bas,bit,cagiran=None):
    from .gorunumler import gorev_payi,para
    from .gorunum_v7 import saat_maliyeti
    if cagiran and not proje_gorebilir_mi(d,cagiran,proje): raise PermissionError('Proje gorunurlugu')
    sonuc={}
    for x in list(d.gorevler.values())+list(d.isler.values()):
        if x.get('proje')!=proje or not x.get('degisiklik_kaynagi'): continue
        e=next(e for e in olaylar(d) if e['olay_kimligi']==x['doguran_olay'])
        if not gun(bas)<=gun(an(e['oldugu_an']))<=gun(bit): continue
        r=sonuc.setdefault(x['degisiklik']['neden'],dict(is_sayisi=0,zaman_degeri=0,atolye_saati=0,maliyet=Decimal(0)))
        r['is_sayisi']+=1
        if x['kimlik'] in d.gorevler:
            r['zaman_degeri']+=x['zaman_degeri']
            satirlar=[(gorev_payi(d,x,t,t,kisi=k),saat_maliyeti(d,k,t)) for t in gunler(bas,bit) for k in {x['kisi']}|{h['kisi'] for h in x.get('kisi_gecmisi',[])}]
        else:
            satirlar=[]
            for a in d.araliklar:
                if a['is']==x['kimlik'] and a['kisi'] and gun(bas)<=a['gun']<=gun(bit) and a['kova'] in ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY'):
                    sa=((a['bitis'] or d.saat.simdi())-a['baslangic']).total_seconds()/3600
                    if a['kova'] in ('CALISMA','YENIDEN_ISLEME'): r['atolye_saati']+=sa
                    satirlar.append((sa,saat_maliyeti(d,a['kisi'],a['gun'])))
        for sa,oran in satirlar:
            if not sa: continue
            r['maliyet']='VERI_EKSIK' if oran=='VERI_EKSIK' or r['maliyet']=='VERI_EKSIK' else r['maliyet']+Decimal(str(sa))*oran
    for r in sonuc.values():
        if r['maliyet']!='VERI_EKSIK': r['maliyet']=para(r['maliyet'])
        if not cagiran or not gorebilir_mi(d,cagiran,'TUTAR'): r.pop('maliyet')
    return sonuc


def gun_onayi_gerekli(d,kisi,tarih):
    b=kisi_birimi(d,kisi,tarih)
    ss=[x for x in d.gun_onay_ayarlari.values() if x['birim']==b and gun(x['gecerli_baslangic'])<=gun(tarih)]
    return max(ss,key=lambda x:(x['gecerli_baslangic'],x['an'],x['kimlik']))['gerekli'] if ss else False


def onay_bekliyor(d,kisi,tarih):
    if not gun_onayi_gerekli(d,kisi,tarih): return False
    from .gorunum_v7 import gun_sonu_raporu
    return gun_sonu_raporu(d,kisi,tarih)['durum']!='ONAYLANDI'


def gun_isleri(d,kisi,t=None):
    if t is not None and an(t)!=d.saat.simdi():
        from .gorunum_v7 import durum
        return gun_isleri(durum(d,t),kisi)
    from .gorunum_v7 import gun_sonu_raporu
    sonuc=[]; simdi=d.saat.simdi()
    if kisi not in d.kisiler: return []
    p=d.kisiler[kisi]
    if p['yaka']=='BEYAZ':
        for tarih in gunler(p['giris_tarihi'],simdi):
            if not istihdamda(d,kisi,tarih) or not kisi_normal(d,kisi,tarih): continue
            if simdi<gun_ani(tarih,d.takvim(tarih,kisi)['mesai_baslangic']): continue
            r=gun_sonu_raporu(d,kisi,tarih)
            gonderildi=any(e['eylem_kodu']=='GUN_SONU.GONDERDIM' for e in r.get('gecmis',[]))
            if not gonderildi or r['durum']=='IADE': sonuc.append(dict(tur='MESAI_SONU',kisi=kisi,gun=str(tarih)))
    gruplar=defaultdict(list)
    for k,p in d.kisiler.items():
        if k==kisi or kisi not in ustler(d,k): continue
        for tarih in gunler(p['giris_tarihi'],simdi):
            if not istihdamda(d,k,tarih) or not kisi_normal(d,k,tarih) or not onay_bekliyor(d,k,tarih): continue
            b=kisi_birimi(d,k,tarih)
            if kisi in yoneticiler(d,b) and k in yoneticiler(d,b): continue
            if simdi<gun_ani(tarih,d.takvim(tarih,k)['mesai_bitis']): continue
            gruplar[(b,str(tarih))].append(k)
    for (b,tarih),ks in sorted(gruplar.items()): sonuc.append(dict(tur='GUN_ONAYI',birim=b,gun=tarih,kisiler=sorted(ks)))
    return sonuc


def hatirlatmalar(d):
    from .gorunum_v7 import gun_sonu_raporu
    simdi=d.saat.simdi(); sonuc=[]
    zorunlu=d.ayar('gun_sonu_raporu_zorunlu',simdi,False)
    if not zorunlu and not d.gun_onay_ayarlari and not any(x['durum']=='GONDERILDI' for x in d.gun_sonu_raporlari.values()): return []
    for kisi,p in d.kisiler.items():
        for tarih in gunler(p['giris_tarihi'],simdi.date()-timedelta(days=1)):
            if not istihdamda(d,kisi,tarih) or not kisi_normal(d,kisi,tarih): continue
            sonraki=tarih+timedelta(days=1)
            for _ in range(370):
                if d.is_gunu(sonraki,kisi): break
                sonraki+=timedelta(days=1)
            esik=gun_ani(sonraki,d.takvim(sonraki,kisi)['mesai_baslangic'])
            ayar=d.ayar('gun_sonu_hatirlatma',simdi,'ERTESI_IS_GUNU')
            if type(ayar) in (int,float): esik+=timedelta(hours=ayar)
            if simdi<esik: continue
            r=gun_sonu_raporu(d,kisi,tarih); gerekli=gun_onayi_gerekli(d,kisi,tarih)
            if r['durum']=='ONAYLANDI': continue
            if p['yaka']=='BEYAZ' and zorunlu and r['durum'] in ('TASLAK','IADE'):
                for alici in sorted({kisi}|(ustler(d,kisi) if gerekli else set())): sonuc.append(dict(kural='R32',alici=alici,kisi=kisi,gun=str(tarih),an=esik))
            if gerekli or (p['yaka']=='BEYAZ' and r['durum'] in ('GONDERILDI','DEGISTI')):
                for alici in sorted(ustler(d,kisi)): sonuc.append(dict(kural='R33',alici=alici,kisi=kisi,gun=str(tarih),an=esik))
    return sonuc


def bekleyen_maliyet(d,bas,bit,proje=None,kisi=None,maas=False,iptal=False):
    from .gorunum_v7 import saat_maliyeti
    from .gorunumler import gorev_payi,para
    toplam=Decimal(0)
    if not d.gun_onay_ayarlari: return para(0)
    def ekle(k,t,sa):
        nonlocal toplam
        if not sa or not onay_bekliyor(d,k,t): return
        oran=saat_maliyeti(d,k,t)
        toplam='VERI_EKSIK' if oran=='VERI_EKSIK' or toplam=='VERI_EKSIK' else toplam+Decimal(str(sa))*oran
    if maas:
        for g in d.gorevler.values():
            if proje and g.get('proje')!=proje: continue
            for t in gunler(bas,bit): ekle(kisi,t,gorev_payi(d,g,t,t,kisi=kisi))
    else:
        from .gorunum_v10_1 import pencere
        pencere_bas,pencere_bit=pencere(bas,bit)
        for a in d.araliklar:
            if not a['kisi'] or (proje and a['proje']!=proje) or (kisi and a['kisi']!=kisi): continue
            if (d.isler.get(a['is'],{}).get('durum')=='IPTAL')!=iptal: continue
            if a['kova'] not in ('CALISMA','YENIDEN_ISLEME','BEKLEME_ARIZA','BEKLEME_ON_IS','BEKLEME_ONAY'): continue
            p,q=max(a['baslangic'],pencere_bas),min(a['bitis'] or d.saat.simdi(),pencere_bit)
            if p<q: ekle(a['kisi'],a['gun'],(q-p).total_seconds()/3600)
    return toplam if toplam=='VERI_EKSIK' else para(toplam)


def onay_uyarilari(d,bas,bit):
    if not d.gun_onay_ayarlari: return []
    sonuc=defaultdict(list)
    for k,p in d.kisiler.items():
        for t in gunler(max(gun(p['giris_tarihi']),gun(bas)),bit):
            if istihdamda(d,k,t) and kisi_normal(d,k,t) and onay_bekliyor(d,k,t): sonuc[(kisi_birimi(d,k,t),str(t))].append(k)
    return [dict(birim=b,gun=t,kisiler=sorted(ks)) for (b,t),ks in sorted(sonuc.items())]


def gorev_listesi(d,kisi):
    return sorted((deepcopy(x) for x in d.gorevler.values() if x['kisi']==kisi and x['durum'] not in ('BITTI','IPTAL')),key=lambda x:({'ACIL':0,'YUKSEK':1,'NORMAL':2}[x.get('oncelik','NORMAL')],x.get('teslim_tarihi') or '9999',x['kimlik']))


def proje_ekleri(d,proje,cagiran=None):
    from .gorunumler import gorev_payi,para
    from .gorunum_v7 import donem_defteri
    from .is_ import emek
    bagli=sorted(k for k,p in d.projeler.items() if p.get('ana_proje')==proje)
    def emegi(p):
        return sum(gorev_payi(d,g,'1900-01-01',d.saat.simdi().date()) for g in d.gorevler.values() if g.get('proje')==p and g['durum']!='IPTAL')+sum(emek(d,x['kimlik'])/60 for x in d.isler.values() if x.get('proje')==p and x['durum']!='IPTAL' and x.get('kisi_sayisi',1)==1)
    son=dict(emek_saat=sum(emegi(p) for p in bagli))
    sonuc=dict(bagli_projeler=bagli,bitis_sonrasi=son,harcanan_emek=emegi(proje))
    if cagiran and gorebilir_mi(d,cagiran,'TUTAR'):
        bas=min((gun(an(e['oldugu_an'])) for e in olaylar(d)),default=d.saat.simdi().date())
        defter=donem_defteri(d,bas,d.saat.simdi().date())
        def tutar(ps):
            ss=[x['tutar'] for x in defter.values() if x['proje'] in ps]
            return 'VERI_EKSIK' if 'VERI_EKSIK' in ss else para(sum(ss,Decimal(0)))
        son['maliyet']=tutar(bagli); sonuc['maliyet']=tutar([proje])
    return sonuc
