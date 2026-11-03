"""Gecen senaryo testlerinin gercek girdilerini ve cevaplarini dondurur.

Test beklentileri once elle hesaplanan sayilari dogrular. Bu kaydedici daha
sonra ayni basarili yurumenin tam cikti sozlesmesini uretir; test sonucunu
degistirmez ve beklenen JSON'u yeniden oynaticidan kopyalamaz.
"""
import contextlib
import functools
import importlib
import json
import re
import shutil
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from irp import Depo
from irp.cihaz import Cihaz
from irp import zaman

KOK=Path(__file__).resolve().parent
PAKET=KOK/'cevap_anahtari'
sys.path.insert(0,str(PAKET))
from yurut import kodla_arg, saat_bilgisi, son_hal, yaz
from karsilastir import kanonik


class Kaydedici:
    def __init__(self):
        self.girdi={'bicim_surumu':3,'depolar':[],'cihaz_denemeleri':[],'saf_sorgular':[]}
        self.bek={'depolar':[],'cihaz_denemeleri':[],'saf_sorgular':[]}
        self.depolar=[]; self.esleme={}; self.derinlik=0; self.geri=[]

    def degistir(self,nesne,ad,yeni):
        self.geri.append((nesne,ad,getattr(nesne,ad))); setattr(nesne,ad,yeni)

    def depo_init(self,asil):
        @functools.wraps(asil)
        def sarmal(d,*args,**kwargs):
            dis = self.derinlik == 0
            self.derinlik+=1
            try: asil(d,*args,**kwargs)
            finally: self.derinlik-=1
            if not dis: return
            self.esleme[id(d)]=len(self.depolar); self.depolar.append(d)
            self.girdi['depolar'].append({'baslangic':saat_bilgisi(d.saat),'yontem':d.yontem,'adimlar':[]})
            self.bek['depolar'].append({'cevaplar':[],'ara_haller':[]})
        return sarmal

    def depo_cagri(self,asil,tur,modul=None,ad=None):
        @functools.wraps(asil)
        def sarmal(d,*args,**kwargs):
            if self.derinlik or id(d) not in self.esleme: return asil(d,*args,**kwargs)
            n=self.esleme[id(d)]
            kayit={'tur':tur,'saat':saat_bilgisi(d.saat),'yontem':d.yontem,
                   'args':kodla_arg(deepcopy(args)),'kwargs':kodla_arg(deepcopy(kwargs))}
            if modul: kayit.update(modul=modul,ad=ad)
            if tur in ('ilerlet','kapanis'): kayit['kontrol']=True
            self.girdi['depolar'][n]['adimlar'].append(kayit)
            self.derinlik+=1
            try:
                sonuc=asil(d,*args,**kwargs)
                cevap={'deger':'KAPANDI' if tur=='kapanis' else kanonik(sonuc)}
            except Exception as h:
                cevap={'hata_turu':type(h).__name__,'neden':str(h)}
                raise
            finally:
                self.derinlik-=1
                self.bek['depolar'][n]['cevaplar'].append(cevap)
                if kayit.get('kontrol'):
                    self.bek['depolar'][n]['ara_haller'].append({'adim':len(self.bek['depolar'][n]['cevaplar'])-1,'son_hal':son_hal(d)})
            return sonuc
        return sarmal

    def saf_cagri(self,asil):
        depo_sarmal=self.depo_cagri(asil,'sorgu',asil.__module__,asil.__name__)
        @functools.wraps(asil)
        def sarmal(*args,**kwargs):
            if self.derinlik: return asil(*args,**kwargs)
            if args and isinstance(args[0],Depo): return depo_sarmal(*args,**kwargs)
            self.girdi['saf_sorgular'].append({'modul':asil.__module__,'ad':asil.__name__,
                                               'args':kodla_arg(deepcopy(args)),'kwargs':kodla_arg(deepcopy(kwargs))})
            self.derinlik+=1
            try:
                sonuc=asil(*args,**kwargs); cevap={'deger':kanonik(sonuc)}
            except Exception as h:
                cevap={'hata_turu':type(h).__name__,'neden':str(h)}; raise
            finally:
                self.derinlik-=1; self.bek['saf_sorgular'].append(cevap)
            return sonuc
        return sarmal

    def cihaz_cagri(self,asil,ad):
        @functools.wraps(asil)
        def sarmal(c,*args,**kwargs):
            if self.derinlik: return asil(c,*args,**kwargs)
            kayit={'ad':ad,'kisi':c.kisi,'harf':c.harf,'saat':saat_bilgisi(c.saat),'veri':kodla_arg(deepcopy(c.veri))}
            if ad=='sayaci_esitle': kayit['bulut_kimlikleri']=sorted(args[0].olaylar)
            else: kayit.update(args=kodla_arg(deepcopy(args)),kwargs=kodla_arg(deepcopy(kwargs)))
            self.girdi['cihaz_denemeleri'].append(kayit); self.derinlik+=1
            try:
                sonuc=asil(c,*args,**kwargs); cevap={'deger':kanonik(sonuc)}
            except Exception as h:
                cevap={'hata_turu':type(h).__name__,'neden':str(h)}; raise
            finally:
                self.derinlik-=1
                self.bek['cihaz_denemeleri'].append({'cevap':cevap,'veri':kanonik(deepcopy(c.veri)),'harf':c.harf})
            return sonuc
        return sarmal

    def __enter__(self):
        self.degistir(Depo,'__init__',self.depo_init(Depo.__init__))
        for ad,tur in [('olay_ekle','olay'),('kurulum','kurulum'),('ilerlet','ilerlet'),('yeniden_kur','yeniden_kur'),('demo_sifirla','demo_sifirla'),('olay_koru','olay_koru'),('cihaz_esitle','cihaz_esitle'),('cihaz_kaydol','cihaz_kaydol')]:
            self.degistir(Depo,ad,self.depo_cagri(getattr(Depo,ad),tur))
        for ad in ('birak','kaldir'):
            self.degistir(Depo,'modul_bildirimi_'+ad,self.depo_cagri(getattr(Depo,'modul_bildirimi_'+ad),'modul_bildirimi','irp.modul_bildirimi',ad))
        for ad in ('olay_kimligi_uret','sayaci_esitle','depo_kayboldu','yeniden_kaydol','ekran_hali','tazelik'):
            self.degistir(Cihaz,ad,self.cihaz_cagri(getattr(Cihaz,ad),ad))
        kapanis=zaman.ay_kapanisi
        for mod in list(sys.modules.values()):
            ad=getattr(mod,'__name__','')
            if not (ad.startswith('testler.') or ad in ('irp.demo','irp.zaman') or ad.startswith('simulasyon.')): continue
            for isim,fn in list(vars(mod).items()):
                if fn is kapanis: self.degistir(mod,isim,self.depo_cagri(kapanis,'kapanis'))
                elif ad.startswith('testler.') and callable(fn) and getattr(fn,'__module__','') in ('irp.gorunumler','irp.gorunum_v6','irp.gorunum_v7','irp.gorunum_v9','irp.gorunum_v10_1','irp.is_','irp.gorev','irp.kisi_gunu','irp.hesap_yetkisi','irp.surum') and isim!='durum':
                    self.degistir(mod,isim,self.saf_cagri(fn))
        return self

    def __exit__(self,*hata):
        for nesne,ad,asil in reversed(self.geri): setattr(nesne,ad,asil)
        for n,d in enumerate(self.depolar):
            self.girdi['depolar'][n]['son_saat']=saat_bilgisi(d.saat)
            self.bek['depolar'][n]['son_hal']=son_hal(d)

    def kaydet(self,yol,ad):
        yol.mkdir(parents=True,exist_ok=True)
        self.girdi['senaryo']=ad
        yaz(yol/(ad+'.girdi.json'),self.girdi); yaz(yol/(ad+'.beklenen.json'),kanonik(self.bek))


def model_kopyala():
    hedef=PAKET/'model/irp'; hedef.mkdir(parents=True,exist_ok=True)
    for p in (KOK/'irp').glob('*.py'): shutil.copyfile(p,hedef/p.name)


def senaryolar():
    model_kopyala()
    moduller=['testler.test_senaryolar','testler.senaryolar_v2','testler.test_v3','testler.test_v4','testler.test_v5','testler.test_v6','testler.test_v7','testler.test_v9','testler.test_v10']
    for m in moduller: importlib.import_module(m)
    kayitlar=[]; gorulen=set()
    for m in moduller:
        mod=sys.modules[m]
        for sinif in vars(mod).values():
            if not isinstance(sinif,type) or not issubclass(sinif,unittest.TestCase) or sinif.__module__!=m: continue
            for ad in unittest.defaultTestLoader.getTestCaseNames(sinif):
                if not re.match(r'test_[SDY]\d',ad): continue
                isim=ad[5:]
                if isim in gorulen: raise ValueError('Tekrar senaryo: '+isim)
                gorulen.add(isim)
                test=sinif(ad); sonuc=unittest.TestResult()
                with Kaydedici() as kayit: test.run(sonuc)
                if not sonuc.wasSuccessful(): raise AssertionError((test.id(),sonuc.errors,sonuc.failures))
                kayit.kaydet(PAKET/'senaryolar',isim)
                kayitlar.append({'senaryo':isim,'test':test.id(),'depo':len(kayit.depolar),'cihaz_deneyi':len(kayit.girdi['cihaz_denemeleri'])})
                print(isim+': donduruldu',flush=True)
    temel={re.match(r'[SDY]\d+',x).group() for x in gorulen}
    bek={f'S{n}' for n in range(1,19)}|{f'D{n}' for n in range(1,5)}|{f'Y{n}' for n in range(1,100)}
    assert temel==bek,(bek-temel,temel-bek)
    yaz(PAKET/'senaryo_dizini.json',{'temel_senaryo':len(temel),'dosya_cifti':len(kayitlar),'senaryolar':kayitlar})


def simulasyon():
    model_kopyala()
    from simulasyon.uret_v3 import uret
    from simulasyon.calistir_v4 import canli_hazirla
    from irp import Saat, an
    from irp import gorunumler
    f,meta=uret(42)
    akis=[(an(meta['gecikmeler'].get(e['olay_kimligi'],e['oldugu_an'])),0,e) for e in f.olaylar]
    akis += [(an(meta['gecikmeler'].get(e['olay_kimligi'],e['oldugu_an'])),2,e) for e in f.olaylar if e['olay_kimligi'] in meta['tekrarlar']]
    akis.append((an('2026-11-01T00:30:00+03:00'),1,None))
    akis.sort(key=lambda x:(x[0],x[1],x[2]['olay_kimligi'] if x[2] else ''))
    sabit={}
    with Kaydedici() as kayit:
        d=Depo(Saat('2026-10-01T00:00:00+03:00'))
        for no,(t,tur,e) in enumerate(akis,1):
            d.saat.ilerlet(t)
            if tur==1: d.yeniden_kur(); zaman.ay_kapanisi(d,'2026-10-01'); continue
            ee=canli_hazirla(e,d,meta,sabit)
            s=d.olay_ekle(ee,oturum=e['kim'],servis=e['giris_sekli']=='AKTARIM',hassas_ek=f.hassas.get(e['olay_kimligi']))
            assert s.get('kod',s['sonuc'])==meta['canli'].get(e['olay_kimligi'],'BASARILI'),(no,s)
            assert not d.isleme_hatalari
            if no%500==0: print(f'Paket simulasyon {no}/{len(akis)}',flush=True)
        d.ilerlet('2026-11-15T18:00:00+03:00'); d.yeniden_kur()
        for ad,args in [('proje_gostergesi',[p]) for p in d.projeler]+[
            ('maas_dagilimi',['K118','2026-10-01']),('adil_performans',['K119','2026-10-01','2026-11-15']),
            ('kim_nerede',['2026-11-02','2026-11-03']),('birim_dolulugu',['2026-11-09','2026-11-13']),
            ('saat_nereye_gitti',['2026-10-19','2026-11-15'])]:
            kayit.depo_cagri(getattr(gorunumler,ad),'sorgu','irp.gorunumler',ad)(d,*args)
    kayit.girdi['tohum']=42
    kayit.kaydet(PAKET/'simulasyon','buyuk')


if __name__=='__main__':
    if '--simulasyon' in sys.argv: simulasyon()
    else: senaryolar()
